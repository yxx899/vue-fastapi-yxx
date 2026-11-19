import csv
import io
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import PlatformContext, TenantUserContext, get_current_tenant_user, get_platform_admin, require_admin_feature
from app.services.tenant_features import ensure_tenant_feature
from app.database import get_db
from app.models.entities import ChatMessage, Document, DocumentStatus, KnowledgeBase, QALog, User

router = APIRouter(prefix="/audit", tags=["审计与统计"])


def _qa_logs_query(
    db: Session,
    tenant_id: int,
    *,
    user_id: int | None = None,
    today_only: bool = False,
    start_date: date | None = None,
    end_date: date | None = None,
    feedback: int | None = None,
):
    q = db.query(QALog).filter(QALog.tenant_id == tenant_id)
    if user_id:
        q = q.filter(QALog.user_id == user_id)
    if today_only:
        today_start = datetime.combine(date.today(), datetime.min.time())
        q = q.filter(QALog.created_at >= today_start)
    if start_date:
        q = q.filter(QALog.created_at >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        q = q.filter(QALog.created_at <= datetime.combine(end_date, datetime.max.time()))
    if feedback is not None:
        q = q.filter(QALog.feedback == feedback)
    return q


@router.get("/logs")
def qa_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: int | None = None,
    today_only: bool = False,
    start_date: date | None = None,
    end_date: date | None = None,
    feedback: int | None = Query(None, ge=-1, le=1),
    ctx: TenantUserContext = Depends(require_admin_feature("audit")),
    db: Session = Depends(get_db),
):
    q = _qa_logs_query(
        db,
        ctx.tenant.id,
        user_id=user_id,
        today_only=today_only,
        start_date=start_date,
        end_date=end_date,
        feedback=feedback,
    )
    total = q.count()
    items = q.order_by(QALog.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "items": [
            {
                "id": i.id,
                "user_id": i.user_id,
                "kb_ids": i.kb_ids,
                "question": i.question,
                "answer": i.answer,
                "answer_preview": (i.answer or "")[:120].replace("\n", " "),
                "sources_json": i.sources_json,
                "feedback": i.feedback,
                "created_at": i.created_at.isoformat(),
            }
            for i in items
        ],
    }


@router.get("/logs/export")
def export_logs(ctx: TenantUserContext = Depends(require_admin_feature("audit")), db: Session = Depends(get_db)):
    ensure_tenant_feature(ctx.tenant, "audit_export")
    items = db.query(QALog).filter(QALog.tenant_id == ctx.tenant.id).order_by(QALog.id.desc()).limit(5000).all()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "user_id", "kb_ids", "question", "answer", "feedback", "created_at"])
    for i in items:
        writer.writerow([i.id, i.user_id, i.kb_ids, i.question, i.answer, i.feedback, i.created_at.isoformat()])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=qa_logs.csv"},
    )


def _delete_qa_logs_batch(
    db: Session,
    tenant_id: int,
    *,
    user_id: int | None = None,
    today_only: bool = False,
    start_date: date | None = None,
    end_date: date | None = None,
    feedback: int | None = None,
) -> int:
    q = _qa_logs_query(
        db,
        tenant_id,
        user_id=user_id,
        today_only=today_only,
        start_date=start_date,
        end_date=end_date,
        feedback=feedback,
    )
    deleted = q.delete(synchronize_session=False)
    db.commit()
    return deleted


@router.post("/logs/actions/batch-delete")
@router.post("/logs/delete-batch")
def delete_qa_logs_batch(
    user_id: int | None = None,
    today_only: bool = False,
    start_date: date | None = None,
    end_date: date | None = None,
    feedback: int | None = Query(None, ge=-1, le=1),
    ctx: TenantUserContext = Depends(require_admin_feature("audit")),
    db: Session = Depends(get_db),
):
    """按与列表相同的筛选条件批量删除（一键删除）。"""
    deleted = _delete_qa_logs_batch(
        db,
        ctx.tenant.id,
        user_id=user_id,
        today_only=today_only,
        start_date=start_date,
        end_date=end_date,
        feedback=feedback,
    )
    return {"message": "已删除", "deleted": deleted}


@router.get("/knowledge-bases")
def audit_kb_list(ctx: TenantUserContext = Depends(require_admin_feature("statistics_dashboard")), db: Session = Depends(get_db)):
    rows = db.query(KnowledgeBase).filter(KnowledgeBase.tenant_id == ctx.tenant.id).order_by(KnowledgeBase.id.desc()).all()
    return {
        "items": [
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "is_active": r.is_active,
                "is_public_in_tenant": r.is_public_in_tenant,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
    }


@router.get("/documents")
def audit_doc_list(ctx: TenantUserContext = Depends(require_admin_feature("statistics_dashboard")), db: Session = Depends(get_db)):
    rows = (
        db.query(Document, KnowledgeBase.name.label("kb_name"))
        .join(KnowledgeBase, Document.kb_id == KnowledgeBase.id)
        .filter(Document.tenant_id == ctx.tenant.id)
        .order_by(Document.id.desc())
        .all()
    )
    return {
        "items": [
            {
                "id": d.id,
                "kb_id": d.kb_id,
                "kb_name": kb_name,
                "filename": d.filename,
                "file_size": d.file_size,
                "status": d.status.value,
                "error_message": d.error_message,
                "created_at": d.created_at.isoformat(),
            }
            for d, kb_name in rows
        ]
    }


@router.get("/documents/failed")
def audit_failed_docs(ctx: TenantUserContext = Depends(require_admin_feature("statistics_dashboard")), db: Session = Depends(get_db)):
    rows = (
        db.query(Document, KnowledgeBase.name.label("kb_name"))
        .join(KnowledgeBase, Document.kb_id == KnowledgeBase.id)
        .filter(Document.tenant_id == ctx.tenant.id, Document.status == DocumentStatus.FAILED)
        .order_by(Document.id.desc())
        .all()
    )
    return {
        "items": [
            {
                "id": d.id,
                "kb_name": kb_name,
                "filename": d.filename,
                "error_message": d.error_message,
                "created_at": d.created_at.isoformat(),
            }
            for d, kb_name in rows
        ]
    }


def _delete_qa_log_row(log_id: int, ctx: TenantUserContext, db: Session) -> None:
    log = db.query(QALog).filter(QALog.id == log_id, QALog.tenant_id == ctx.tenant.id).first()
    if not log:
        raise HTTPException(status_code=404, detail="记录不存在")
    db.delete(log)
    db.commit()


@router.delete("/logs/{log_id}")
def delete_qa_log(
    log_id: int,
    ctx: TenantUserContext = Depends(require_admin_feature("audit")),
    db: Session = Depends(get_db),
):
    _delete_qa_log_row(log_id, ctx, db)
    return {"message": "已删除"}


@router.post("/logs/{log_id}/delete")
def delete_qa_log_post(
    log_id: int,
    ctx: TenantUserContext = Depends(require_admin_feature("audit")),
    db: Session = Depends(get_db),
):
    """部分环境对 DELETE 支持不佳时的备用接口。"""
    _delete_qa_log_row(log_id, ctx, db)
    return {"message": "已删除"}


@router.get("/dashboard")
def tenant_dashboard(ctx: TenantUserContext = Depends(require_admin_feature("statistics_dashboard")), db: Session = Depends(get_db)):
    tid = ctx.tenant.id
    today_start = datetime.combine(date.today(), datetime.min.time())
    kb_count = db.query(KnowledgeBase).filter(KnowledgeBase.tenant_id == tid).count()
    doc_count = db.query(Document).filter(Document.tenant_id == tid).count()
    qa_total = db.query(QALog).filter(QALog.tenant_id == tid).count()
    qa_today = db.query(QALog).filter(QALog.tenant_id == tid, QALog.created_at >= today_start).count()
    good = db.query(QALog).filter(QALog.tenant_id == tid, QALog.feedback == 1).count()
    bad = db.query(QALog).filter(QALog.tenant_id == tid, QALog.feedback == -1).count()
    failed_docs = db.query(Document).filter(Document.tenant_id == tid, Document.status == DocumentStatus.FAILED).count()
    return {
        "kb_count": kb_count,
        "doc_count": doc_count,
        "qa_total": qa_total,
        "qa_today": qa_today,
        "feedback_good": good,
        "feedback_bad": bad,
        "failed_documents": failed_docs,
    }
