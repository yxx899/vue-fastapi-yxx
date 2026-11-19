import json
import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import TenantUserContext, get_current_tenant_user
from app.core.permissions import list_accessible_kb_ids
from app.database import get_db
from app.models.entities import ChatMessage, ChatSession, KnowledgeBase, QALog
from app.services.message_sanitize import strip_legacy_qwen_notice
from app.services.rag import sources_to_json, stream_demo_answer
from app.services.rag_graph import run_rag_stream
from app.services.tenant_features import ensure_tenant_feature
from app.services.tenant_limits import ensure_tenant_active

# 新建会话里的指代追问：那/它/这个… 需要跨会话记忆
_FOLLOWUP_RE = re.compile(
    r"(那|它|这个|那个|上面|刚才|继续|还有|呢\s*$|怎么样|如何|多少钱|薪资)"
)

router = APIRouter(prefix="/chat", tags=["对话"])


class SessionCreateIn(BaseModel):
    title: str = "新对话"
    kb_ids: list[int] = Field(default_factory=list)


class SessionOut(BaseModel):
    id: int
    title: str
    kb_ids: list[int]
    updated_at: str


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    sources: list | None
    feedback: int | None
    created_at: str


class ChatIn(BaseModel):
    session_id: int | None = None
    kb_ids: list[int]
    question: str = Field(min_length=1, max_length=4000)


class FeedbackIn(BaseModel):
    feedback: int = Field(ge=-1, le=1)


def _parse_kb_ids(raw: str) -> list[int]:
    if not raw:
        return []
    return [int(x) for x in raw.split(",") if x.strip().isdigit()]


def _materialize_answer(stream, question: str, sources: list) -> str:
    parts: list[str] = []
    try:
        for chunk in stream:
            if chunk:
                parts.append(chunk)
    except Exception as e:
        parts.append(f"\n[错误] {e}")
    text = "".join(parts).strip()
    if not text and sources:
        text = "".join(stream_demo_answer(question, sources)).strip()
    return text


def _validate_kb_ids(db: Session, ctx: TenantUserContext, kb_ids: list[int]) -> list[int]:
    if not kb_ids:
        raise HTTPException(status_code=400, detail="请至少选择一个知识库")
    allowed = set(list_accessible_kb_ids(db, ctx.user))
    for kid in kb_ids:
        if kid not in allowed:
            raise HTTPException(status_code=403, detail=f"无知识库 {kid} 的访问权限")
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kid).first()
        if not kb or not kb.is_active:
            raise HTTPException(status_code=400, detail=f"知识库 {kid} 不可用")
    return kb_ids


def _is_likely_followup(question: str) -> bool:
    q = (question or "").strip()
    if not q:
        return False
    if len(q) <= 24 and _FOLLOWUP_RE.search(q):
        return True
    return q.startswith(("那", "它", "这个", "那个", "上面", "刚才", "继续"))


def _load_cross_session_history(
    db: Session,
    *,
    tenant_id: int,
    user_id: int,
    exclude_session_id: int,
    limit: int,
) -> list[dict]:
    """取该用户其他会话中最近的消息，作为新建对话的记忆。"""
    if limit <= 0:
        return []
    rows = (
        db.query(ChatMessage)
        .join(ChatSession, ChatMessage.session_id == ChatSession.id)
        .filter(
            ChatSession.tenant_id == tenant_id,
            ChatSession.user_id == user_id,
            ChatSession.id != exclude_session_id,
            ChatMessage.role.in_(("user", "assistant")),
        )
        .order_by(ChatMessage.id.desc())
        .limit(limit)
        .all()
    )
    rows = list(reversed(rows))
    out: list[dict] = []
    for m in rows:
        content = (m.content or "").strip()
        if not content:
            continue
        if m.role == "assistant" and len(content) > 1200:
            content = content[:1200] + "…"
        out.append({"role": m.role, "content": content})
    return out


def _previous_session_kb_ids(
    db: Session,
    *,
    tenant_id: int,
    user_id: int,
    exclude_session_id: int,
    allowed: set[int],
) -> list[int]:
    """上一会话用过的知识库，供指代追问时补检索。"""
    prev = (
        db.query(ChatSession)
        .filter(
            ChatSession.tenant_id == tenant_id,
            ChatSession.user_id == user_id,
            ChatSession.id != exclude_session_id,
        )
        .order_by(ChatSession.updated_at.desc())
        .first()
    )
    if not prev:
        return []
    return [i for i in _parse_kb_ids(prev.kb_ids or "") if i in allowed]


@router.get("/sessions")
def list_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    ctx: TenantUserContext = Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
):
    q = db.query(ChatSession).filter(ChatSession.tenant_id == ctx.tenant.id, ChatSession.user_id == ctx.user.id)
    total = q.count()
    items = q.order_by(ChatSession.updated_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "items": [
            SessionOut(
                id=s.id,
                title=s.title,
                kb_ids=_parse_kb_ids(s.kb_ids),
                updated_at=s.updated_at.isoformat(),
            )
            for s in items
        ],
    }


@router.get("/history")
def my_qa_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = Query(None, max_length=200),
    ctx: TenantUserContext = Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
):
    """当前登录用户自己的历史问答（可按关键词搜问题/回答）。"""
    ensure_tenant_feature(ctx.tenant, "chat")
    q = (
        db.query(ChatMessage)
        .join(ChatSession, ChatMessage.session_id == ChatSession.id)
        .filter(
            ChatSession.tenant_id == ctx.tenant.id,
            ChatSession.user_id == ctx.user.id,
            ChatMessage.role == "user",
        )
    )
    kw = (keyword or "").strip()
    if kw:
        # 只按「问题」关键词搜索，不搜回答正文
        q = q.filter(ChatMessage.content.contains(kw))

    total = q.count()
    user_msgs = q.order_by(ChatMessage.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    session_ids = {m.session_id for m in user_msgs}
    titles = {}
    if session_ids:
        for s in db.query(ChatSession).filter(ChatSession.id.in_(session_ids)).all():
            titles[s.id] = s.title

    items = []
    for um in user_msgs:
        am = (
            db.query(ChatMessage)
            .filter(
                ChatMessage.session_id == um.session_id,
                ChatMessage.id > um.id,
                ChatMessage.role == "assistant",
            )
            .order_by(ChatMessage.id.asc())
            .first()
        )
        answer = strip_legacy_qwen_notice(am.content) if am else ""
        preview = answer.replace("\n", " ").strip()
        if len(preview) > 280:
            preview = preview[:280] + "…"
        items.append(
            {
                "session_id": um.session_id,
                "session_title": titles.get(um.session_id) or "对话",
                "question_id": um.id,
                "question": um.content,
                "answer": answer,
                "answer_preview": preview,
                "feedback": am.feedback if am else None,
                "created_at": um.created_at.isoformat(),
            }
        )
    return {"total": total, "items": items}


@router.post("/sessions", response_model=SessionOut)
def create_session(body: SessionCreateIn, ctx: TenantUserContext = Depends(get_current_tenant_user), db: Session = Depends(get_db)):
    ensure_tenant_active(ctx.tenant)
    ensure_tenant_feature(ctx.tenant, "chat")
    kb_ids = _validate_kb_ids(db, ctx, body.kb_ids)
    session = ChatSession(
        tenant_id=ctx.tenant.id,
        user_id=ctx.user.id,
        title=body.title,
        kb_ids=",".join(str(i) for i in kb_ids),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return SessionOut(id=session.id, title=session.title, kb_ids=kb_ids, updated_at=session.updated_at.isoformat())


@router.put("/sessions/{session_id}")
def update_session(
    session_id: int,
    title: str,
    ctx: TenantUserContext = Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
):
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == ctx.user.id, ChatSession.tenant_id == ctx.tenant.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    session.title = title
    db.commit()
    return {"message": "已更新"}


@router.delete("/sessions/{session_id}")
def delete_session(session_id: int, ctx: TenantUserContext = Depends(get_current_tenant_user), db: Session = Depends(get_db)):
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == ctx.user.id, ChatSession.tenant_id == ctx.tenant.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()
    db.delete(session)
    db.commit()
    return {"message": "已删除"}


@router.get("/sessions/{session_id}/messages")
def list_messages(session_id: int, ctx: TenantUserContext = Depends(get_current_tenant_user), db: Session = Depends(get_db)):
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == ctx.user.id, ChatSession.tenant_id == ctx.tenant.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    msgs = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.id).all()
    out = []
    for m in msgs:
        sources = json.loads(m.sources_json) if m.sources_json else None
        text = m.content
        if m.role == "assistant":
            text = strip_legacy_qwen_notice(text)
        out.append(
            MessageOut(
                id=m.id,
                role=m.role,
                content=text,
                sources=sources,
                feedback=m.feedback,
                created_at=m.created_at.isoformat(),
            )
        )
    return out


@router.post("/stream")
def chat_stream(
    body: ChatIn,
    request: Request,
    ctx: TenantUserContext = Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
):
    ensure_tenant_active(ctx.tenant)
    ensure_tenant_feature(ctx.tenant, "chat")
    kb_ids = _validate_kb_ids(db, ctx, body.kb_ids)

    session: ChatSession | None = None
    if body.session_id:
        session = (
            db.query(ChatSession)
            .filter(
                ChatSession.id == body.session_id,
                ChatSession.user_id == ctx.user.id,
                ChatSession.tenant_id == ctx.tenant.id,
            )
            .first()
        )
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
    else:
        session = ChatSession(
            tenant_id=ctx.tenant.id,
            user_id=ctx.user.id,
            title=body.question[:30],
            kb_ids=",".join(str(i) for i in kb_ids),
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    user_msg = ChatMessage(session_id=session.id, role="user", content=body.question)
    db.add(user_msg)
    session.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user_msg)

    prev_rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id, ChatMessage.id < user_msg.id)
        .order_by(ChatMessage.id.asc())
        .all()
    )
    max_msgs = max(2, settings.rag_history_turns * 2)
    prev_rows = prev_rows[-max_msgs:]
    history = [
        {"role": m.role, "content": m.content}
        for m in prev_rows
        if m.role in ("user", "assistant") and (m.content or "").strip()
    ]

    # 新建会话 / 本会话几乎没有上文时：注入其他会话最近对话作为记忆
    used_cross_memory = False
    followup = _is_likely_followup(body.question)
    cross_limit = max(2, settings.rag_cross_session_turns * 2)
    if settings.rag_cross_session_enabled and (len(history) < 2 or followup):
        need = max(cross_limit - len(history), cross_limit if followup and len(history) < 2 else 0)
        if need > 0:
            cross = _load_cross_session_history(
                db,
                tenant_id=ctx.tenant.id,
                user_id=ctx.user.id,
                exclude_session_id=session.id,
                limit=need,
            )
            if cross:
                history = (cross + history)[-max_msgs:]
                used_cross_memory = True

    # 指代追问：补上「上一会话」用过的知识库，避免新建后选错库答不上「那它的薪资」
    rag_kb_ids = list(kb_ids)
    if settings.rag_cross_session_enabled and followup:
        allowed = set(list_accessible_kb_ids(db, ctx.user))
        extra = _previous_session_kb_ids(
            db,
            tenant_id=ctx.tenant.id,
            user_id=ctx.user.id,
            exclude_session_id=session.id,
            allowed=allowed,
        )
        for kid in extra:
            if kid not in rag_kb_ids:
                kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kid).first()
                if kb and kb.is_active:
                    rag_kb_ids.append(kid)

    sid = session.id
    question_text = body.question
    tenant_id = ctx.tenant.id
    user_id = ctx.user.id

    def event_gen():
        from app.database import SessionLocal

        answer_parts: list[str] = []
        yield f"data: {json.dumps({'type': 'session', 'session_id': sid}, ensure_ascii=False)}\n\n"
        if used_cross_memory:
            status = "已记住最近对话，正在结合记忆检索知识库…"
        elif history:
            status = "正在结合上文检索知识库并生成回答…"
        else:
            status = "正在检索知识库并生成回答…"
        yield f"data: {json.dumps({'type': 'status', 'content': status}, ensure_ascii=False)}\n\n"
        sources: list = []
        try:
            stream, sources = run_rag_stream(tenant_id, rag_kb_ids, question_text, history)
            answer = _materialize_answer(stream, question_text, sources)
        except Exception as e:
            err = str(e) or "问答处理失败"
            yield f"data: {json.dumps({'type': 'error', 'message': err}, ensure_ascii=False)}\n\n"
            answer = f"[错误] {err}"

        if not answer:
            answer = "未能生成回答，请检查知识库文档是否解析成功，或稍后重试。"
        answer = strip_legacy_qwen_notice(answer)

        # 服务端先生成完整答案，再分块推送，避免流式 SDK/代理导致前端收不到 delta
        step = 64
        for i in range(0, len(answer), step):
            if request.is_disconnected():
                break
            piece = answer[i : i + step]
            answer_parts.append(piece)
            yield f"data: {json.dumps({'type': 'delta', 'content': piece}, ensure_ascii=False)}\n\n"
        sources_json = sources_to_json(sources)
        ai_message_id = None
        save_db = SessionLocal()
        try:
            ai_msg = ChatMessage(
                session_id=sid,
                role="assistant",
                content=answer,
                sources_json=sources_json,
            )
            save_db.add(ai_msg)
            save_db.add(
                QALog(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    kb_ids=",".join(str(i) for i in kb_ids),
                    question=question_text,
                    answer=answer,
                    sources_json=sources_json,
                )
            )
            save_db.commit()
            save_db.refresh(ai_msg)
            ai_message_id = ai_msg.id
        finally:
            save_db.close()
        yield f"data: {json.dumps({'type': 'answer', 'content': answer}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'type': 'sources', 'sources': sources}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'message_id': ai_message_id}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/messages/{message_id}/feedback")
def message_feedback(
    message_id: int,
    body: FeedbackIn,
    ctx: TenantUserContext = Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
):
    msg = db.query(ChatMessage).filter(ChatMessage.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="消息不存在")
    session = db.query(ChatSession).filter(ChatSession.id == msg.session_id).first()
    if not session or session.user_id != ctx.user.id:
        raise HTTPException(status_code=403, detail="无权限")
    msg.feedback = body.feedback
    if msg.role == "assistant":
        prev_user = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == msg.session_id, ChatMessage.id < msg.id, ChatMessage.role == "user")
            .order_by(ChatMessage.id.desc())
            .first()
        )
        if prev_user:
            log = (
                db.query(QALog)
                .filter(
                    QALog.tenant_id == ctx.tenant.id,
                    QALog.user_id == ctx.user.id,
                    QALog.question == prev_user.content,
                )
                .order_by(QALog.id.desc())
                .first()
            )
            if log:
                log.feedback = body.feedback
    db.commit()
    return {"message": "感谢反馈"}
