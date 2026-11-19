import json
import re
from collections.abc import Iterator

from app.config import settings
from app.services.embedding import embed_query
from app.services.qwen_client import chat_complete, qwen_http_enabled, stream_chat
from app.services.vector_store import query_vectors

# 知识库未命中时的固定婉拒（不调用自身知识作答）
NO_CONTEXT_ANSWER = (
    "我把知识库翻了个底朝天，这题好像还没入库～"
    "我只能依据已上传的文档回答，暂时没法用自己的知识替你补答。"
    "把相关资料丢进知识库后，再来问我就不一样啦。"
)

SYSTEM_PROMPT = """你是企业知识库助手，只依据检索到的企业文档作答，支持多轮对话。
回答规则：
1. 只能依据「本轮检索上下文」与对话历史作答；有依据时简洁说明，并可注明文档名称。
2. 检索片段必须能真正回答用户问题才算命中。下列情况一律当作未命中：
   - 只是碰巧撞上个别词；
   - 文档把问句当 Agent/提示词/教学示例，并不能回答本题；
   - 片段答非所问。
3. 未命中时：用一两句轻松、委婉的话说明知识库里没有，并提醒可以上传文档；语气可幽默，但不要油腻、不要嘲讽。
4. 严禁使用你自己的通用知识、常识或外部信息作答；未命中就停，不要补讲、不要展开科普。
5. 不要编造「某份企业文档里写了……」。
6. 理解指代与追问（如「这个」「上面」「那薪资呢」）；对话历史可能来自用户最近其他会话，请据此理解「它/那个」指代的对象。"""

_STOPWORDS = {
    "哪些",
    "什么",
    "怎么",
    "如何",
    "是否",
    "可以",
    "一个",
    "我们",
    "你们",
    "这个",
    "那个",
    "没有",
    "相关",
    "内容",
    "问题",
    "多少",
    "怎样",
    "为何",
    "因为",
    "所以",
    "以及",
    "或者",
    "如果",
    "需要",
    "进行",
    "一下",
    "请问",
    "帮我",
    "告诉",
    "介绍",
    "今天",
    "明天",
    "昨天",
    "现在",
    "目前",
    "一下",
}

# 单独出现时区分度太低，不能只靠这些词判定「相关」
_WEAK_TERMS = {
    "模型",
    "语言",
    "开发",
    "使用",
    "系统",
    "数据",
    "功能",
    "代码",
    "文件",
    "学习",
    "训练",
    "调用",
    "返回",
    "输入",
    "输出",
    "任务",
    "用户",
    "结果",
    "执行",
    "创建",
    "实现",
}

# 双字但区分度高，追问「薪资怎么样」必须能命中
_IMPORTANT_SHORT = {
    "薪资",
    "工资",
    "年薪",
    "月薪",
    "待遇",
    "技能",
    "职责",
    "前景",
    "入行",
    "岗位",
    "赛道",
}


def _meaningful_terms(question: str) -> list[str]:
    """抽取可用于匹配文档的词：英文词 + 中文片段/二元组/三元组。"""
    q = (question or "").lower().strip()
    terms: list[str] = []
    terms.extend(re.findall(r"[a-z]{3,}", q))
    for run in re.findall(r"[\u4e00-\u9fff]{2,}", q):
        terms.append(run)
        if len(run) >= 4:
            for i in range(len(run) - 1):
                terms.append(run[i : i + 2])
            for i in range(len(run) - 2):
                terms.append(run[i : i + 3])
    seen: set[str] = set()
    out: list[str] = []
    for t in terms:
        if t in seen or t in _STOPWORDS or t.isdigit():
            continue
        seen.add(t)
        out.append(t)
    return out


def _rank_sources_by_question(sources: list[dict], question: str) -> list[dict]:
    terms = _meaningful_terms(question)
    if not terms:
        return sources

    def score(s: dict) -> int:
        text = (s.get("snippet") or "").lower()
        pts = sum(3 if t in text else 0 for t in terms)
        if s.get("lex_hits"):
            pts += int(s["lex_hits"]) * 2
        return pts

    ranked = sorted(sources, key=score, reverse=True)
    if score(ranked[0]) > 0:
        return ranked
    return sources


def _primary_excerpt(ranked: list[dict], limit: int = 2400) -> str:
    if not ranked:
        return ""
    parts: list[str] = []
    total = 0
    seen: set[str] = set()
    for s in ranked[:4]:
        sn = (s.get("snippet") or "").strip()
        if not sn or sn in seen:
            continue
        seen.add(sn)
        room = limit - total
        if room <= 0:
            break
        if len(sn) > room:
            parts.append(sn[:room] + "…")
            break
        parts.append(sn)
        total += len(sn) + 2
    return "\n\n".join(parts)


def _strong_terms(question: str) -> list[str]:
    """用于判定相关性的较强关键词（长词 / 英文优先）。"""
    terms = _meaningful_terms(question)
    strong = []
    for t in terms:
        if t in _WEAK_TERMS or t in _STOPWORDS:
            continue
        if (
            len(t) >= 3
            or t in _IMPORTANT_SHORT
            or re.fullmatch(r"[a-z][a-z0-9_-]{1,}", t)
        ):
            strong.append(t)
    # 长短语优先
    return sorted(set(strong), key=len, reverse=True)


def _filter_relevant(sources: list[dict], question: str) -> list[dict]:
    """关键词重合为主；真实向量可用时辅以距离阈值。纯乱码/无有效词直接拒答。"""
    if not sources:
        return []
    terms = _meaningful_terms(question)
    strong = _strong_terms(question)
    if not terms:
        return []

    max_dist = settings.rag_max_distance
    use_distance = not settings.embedding_mock
    kept: list[dict] = []
    for s in sources:
        text = (s.get("snippet") or "").lower()
        hits = [t for t in terms if t in text]
        if not hits:
            continue
        strong_hits = [t for t in strong if t in text]
        # 至少命中一个强词；否则弱词再多也不算相关
        if not strong_hits:
            continue
        dist = s.get("distance")
        if use_distance and dist is not None and dist > max_dist:
            continue
        item = dict(s)
        item["lex_hits"] = len(hits) + len(strong_hits) * 3
        kept.append(item)

    if not kept:
        return []
    kept.sort(key=lambda x: (-int(x.get("lex_hits") or 0), x.get("distance") or 1.0))
    # 弱相关（只撞到个别词）当作未命中，避免教学示例等误引
    top = int(kept[0].get("lex_hits") or 0)
    if top < 8:
        return []
    return kept


def _keyword_sources(tenant_id: int, kb_ids: list[int], question: str, *, limit: int = 8) -> list[dict]:
    """数据库关键词检索，弥补 mock 向量不准的问题。"""
    strong = _strong_terms(question)
    if not strong or not kb_ids:
        return []
    from sqlalchemy import or_

    from app.database import SessionLocal
    from app.models.entities import Document, DocumentChunk

    db = SessionLocal()
    try:
        conds = [DocumentChunk.content.contains(t) for t in strong[:5]]
        rows = (
            db.query(DocumentChunk, Document.filename)
            .join(Document, DocumentChunk.document_id == Document.id)
            .filter(
                DocumentChunk.tenant_id == tenant_id,
                Document.kb_id.in_(kb_ids),
                or_(*conds),
            )
            .order_by(DocumentChunk.id.asc())
            .limit(limit * 3)
            .all()
        )
        out: list[dict] = []
        seen: set[str] = set()
        for chunk, filename in rows:
            sn = (chunk.content or "").strip()
            if not sn or sn in seen:
                continue
            seen.add(sn)
            text_l = sn.lower()
            strong_hits = [t for t in strong if t in text_l or t in sn]
            if not strong_hits:
                continue
            out.append(
                {
                    "document_name": filename or "未知文档",
                    "snippet": sn[:1200],
                    "chunk_index": chunk.chunk_index,
                    "distance": 0.01,
                    "lex_hits": len(strong_hits) * 4,
                }
            )
            if len(out) >= limit:
                break
        return out
    finally:
        db.close()


def build_search_query(question: str, history: list[dict] | None = None) -> str:
    """把最近用户问句拼进检索，便于「那薪资呢」这类追问命中文档。"""
    q = (question or "").strip()
    if not history:
        return q
    prev_users = [
        (m.get("content") or "").strip()
        for m in history
        if m.get("role") == "user" and (m.get("content") or "").strip()
    ][-2:]
    if not prev_users:
        return q
    # 当前问句放前面，避免被上文「技能」等词抢走排序
    merged = " ".join([q, *prev_users])
    return merged[:500]


def _expand_with_neighbors(
    tenant_id: int, sources: list[dict], *, window: int = 1
) -> list[dict]:
    """命中切片前后各扩一段，避免「薪资区间：一线城市」后数字落在下一片。"""
    if not sources:
        return sources
    from app.database import SessionLocal
    from app.models.entities import Document, DocumentChunk

    db = SessionLocal()
    try:
        expanded: list[dict] = []
        seen: set[str] = set()
        for s in sources:
            sn0 = (s.get("snippet") or "").strip()
            if not sn0:
                continue
            key0 = sn0[:120]
            if key0 not in seen:
                seen.add(key0)
                expanded.append(s)

            doc_name = s.get("document_name")
            idx = s.get("chunk_index")
            if doc_name is None or idx is None:
                continue
            try:
                idx_i = int(idx)
            except (TypeError, ValueError):
                continue
            for nidx in range(idx_i - window, idx_i + window + 1):
                if nidx == idx_i or nidx < 0:
                    continue
                row = (
                    db.query(DocumentChunk, Document.filename)
                    .join(Document, DocumentChunk.document_id == Document.id)
                    .filter(
                        DocumentChunk.tenant_id == tenant_id,
                        Document.filename == doc_name,
                        DocumentChunk.chunk_index == nidx,
                    )
                    .first()
                )
                if not row:
                    continue
                chunk, filename = row
                sn = (chunk.content or "").strip()
                if not sn:
                    continue
                key = sn[:120]
                if key in seen:
                    continue
                seen.add(key)
                expanded.append(
                    {
                        "document_name": filename or doc_name,
                        "snippet": sn[:1200],
                        "chunk_index": chunk.chunk_index,
                        "distance": s.get("distance"),
                        "lex_hits": int(s.get("lex_hits") or 0) + 2,
                    }
                )
        return expanded
    finally:
        db.close()


def retrieve_context(
    tenant_id: int,
    kb_ids: list[int],
    question: str,
    *,
    filter_question: str | None = None,
    rank_question: str | None = None,
) -> tuple[str, list[dict]]:
    """filter_question：关键词过滤用的文本；rank_question：最终排序优先用当前追问。"""
    rank_q = (rank_question or question or "").strip()
    q_emb = embed_query(question)
    top_k = max(settings.rag_top_k, 8)
    result = query_vectors(q_emb, tenant_id, kb_ids, top_k)
    docs = (result.get("documents") or [[]])[0]
    metas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]
    sources: list[dict] = []
    for i, content in enumerate(docs):
        meta = metas[i] if i < len(metas) else {}
        dist = distances[i] if i < len(distances) else None
        name = meta.get("document_name", "未知文档")
        snippet = content[:1200]
        sources.append(
            {
                "document_name": name,
                "snippet": snippet,
                "chunk_index": meta.get("chunk_index", i),
                "distance": dist,
            }
        )
    # 关键词通道：检索问句 + 当前追问各捞一轮
    sources.extend(_keyword_sources(tenant_id, kb_ids, question, limit=top_k))
    if rank_q and rank_q != question:
        sources.extend(_keyword_sources(tenant_id, kb_ids, rank_q, limit=top_k))

    filter_q = (filter_question or question).strip()
    filtered = _filter_relevant(sources, rank_q or filter_q)
    if not filtered and filter_q != (rank_q or ""):
        filtered = _filter_relevant(sources, filter_q)
    if not filtered and filter_q != question:
        filtered = _filter_relevant(sources, question)
    if not filtered:
        filtered = _filter_relevant(
            _keyword_sources(tenant_id, kb_ids, rank_q or question, limit=top_k),
            rank_q or question,
        )
    sources = filtered
    if not sources:
        return "", []
    # 按当前问句排序，再拼相邻切片，避免数字被截断
    uniq: list[dict] = []
    seen: set[str] = set()
    for s in _rank_sources_by_question(sources, rank_q or filter_q):
        key = (s.get("snippet") or "")[:120]
        if key in seen:
            continue
        seen.add(key)
        uniq.append(s)
    sources = _expand_with_neighbors(tenant_id, uniq[: settings.rag_top_k])
    # 扩完后再按当前问句排一次
    sources = _rank_sources_by_question(sources, rank_q or filter_q)
    parts: list[str] = []
    for i, s in enumerate(sources[: settings.rag_top_k], start=1):
        parts.append(f"[{i}] 文档《{s['document_name']}》:\n{s['snippet']}")
    return "\n\n".join(parts), sources[: settings.rag_top_k]


def build_prompt(
    question: str,
    context: str,
    history: list[dict] | None = None,
    *,
    from_kb: bool = True,
) -> list[dict]:
    msgs: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in history or []:
        role = m.get("role")
        content = (m.get("content") or "").strip()
        if role not in ("user", "assistant") or not content:
            continue
        if role == "assistant" and len(content) > 1500:
            content = content[:1500] + "…"
        msgs.append({"role": role, "content": content})
    if from_kb and (context or "").strip():
        ctx = context.strip()
        tip = (
            "请只根据检索上下文回答本题；把上下文里能回答的要点写全（含数字、区间），"
            "不要写「后文被截断」「未显示具体数值」这类话——若某片段不完整，请综合其他片段补齐。"
            "若整体仍答不上或只是教学/Agent示例：轻松委婉说明知识库没有，提醒可上传文档；"
            "严禁用自身通用知识补答，也不要硬引无关片段。"
        )
    else:
        ctx = "（本轮知识库未检索到相关内容）"
        tip = (
            "请轻松委婉说明知识库没有相关资料，并提醒上传文档后再问；"
            "严禁用自身知识展开回答，两三句话即可。"
        )
    msgs.append(
        {
            "role": "user",
            "content": f"本轮检索上下文：\n{ctx}\n\n本轮用户问题：{question}\n\n{tip}",
        }
    )
    return msgs


def stream_demo_answer(
    question: str,
    sources: list[dict],
    *,
    mode: str = "no_key",
) -> Iterator[str]:
    relevant = _filter_relevant(sources, question) if sources else []
    if not relevant:
        yield NO_CONTEXT_ANSWER
        return
    ranked = _rank_sources_by_question(relevant, question)
    doc = ranked[0].get("document_name", "知识库文档")
    excerpt = _primary_excerpt(ranked)
    yield "【根据知识库整理】\n\n"
    yield f"问题：{question}\n\n"
    yield f"（摘自《{doc}》等，共 {len(ranked)} 段检索结果）\n\n"
    yield excerpt


def stream_qwen_answer(
    messages: list[dict],
    *,
    question: str = "",
    sources: list[dict] | None = None,
    allow_empty_sources: bool = True,
) -> Iterator[str]:
    src = sources or []
    if not qwen_http_enabled():
        yield from stream_demo_answer(question, src, mode="fallback")
        return
    try:
        yield from stream_chat(messages)
    except RuntimeError:
        yield from stream_demo_answer(question, src, mode="fallback")


def answer_with_qwen(
    messages: list[dict],
    *,
    question: str = "",
    sources: list[dict] | None = None,
    allow_empty_sources: bool = True,
) -> str:
    """优先千问；仅依据知识库上下文作答。"""
    src = sources or []
    if not qwen_http_enabled():
        return "".join(stream_demo_answer(question, src, mode="fallback"))
    try:
        return chat_complete(messages)
    except RuntimeError:
        return "".join(stream_demo_answer(question, src, mode="fallback"))


def sources_to_json(sources: list[dict]) -> str:
    return json.dumps(sources, ensure_ascii=False)
