import os
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import TenantUserContext, get_current_tenant_user, require_admin_feature, require_tenant_admin
from app.core.permissions import user_can_access_kb, user_can_manage_kb
from app.database import get_db
from app.models.entities import Document, DocumentStatus, KnowledgeBase
from app.services.document_pipeline import delete_document_vectors, process_document
from app.services.tenant_features import ensure_tenant_feature
from app.services.tenant_limits import check_document_quota, check_file_size, ensure_tenant_active

router = APIRouter(prefix="/documents", tags=["文档"])

ALLOWED_EXT = {".pdf", ".md", ".markdown", ".txt", ".docx", ".doc"}


def _ensure_upload_dir():
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)


def _process_document_task(document_id: int):
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        process_document(db, document_id)
    finally:
        db.close()


@router.get("")
def list_documents(
    kb_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    ctx: TenantUserContext = Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
):
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id, KnowledgeBase.tenant_id == ctx.tenant.id).first()
    if not kb or not user_can_access_kb(db, ctx.user, kb):
        raise HTTPException(status_code=403, detail="无权限")
    q = db.query(Document).filter(Document.kb_id == kb_id, Document.tenant_id == ctx.tenant.id)
    total = q.count()
    items = q.order_by(Document.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "can_manage": user_can_manage_kb(db, ctx.user, kb),
        "items": [
            {
                "id": d.id,
                "kb_id": d.kb_id,
                "filename": d.filename,
                "file_size": d.file_size,
                "status": d.status.value,
                "error_message": d.error_message,
                "uploader_id": d.uploader_id,
                "created_at": d.created_at.isoformat(),
            }
            for d in items
        ],
    }


@router.post("/upload")
async def upload_document(
    kb_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    ctx: TenantUserContext = Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
):
    ensure_tenant_active(ctx.tenant)
    ensure_tenant_feature(ctx.tenant, "document_upload")
    check_document_quota(db, ctx.tenant)
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id, KnowledgeBase.tenant_id == ctx.tenant.id).first()
    if not kb or not kb.is_active:
        raise HTTPException(status_code=404, detail="知识库不可用")
    if not user_can_manage_kb(db, ctx.user, kb):
        raise HTTPException(status_code=403, detail="需要管理权限才能上传")

    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail="不支持的文件类型")

    content = await file.read()
    check_file_size(ctx.tenant, len(content))

    _ensure_upload_dir()
    safe_name = f"{uuid.uuid4().hex}{ext}"
    rel_dir = Path(settings.upload_dir) / str(ctx.tenant.id) / str(kb_id)
    rel_dir.mkdir(parents=True, exist_ok=True)
    file_path = rel_dir / safe_name
    file_path.write_bytes(content)

    doc = Document(
        tenant_id=ctx.tenant.id,
        kb_id=kb_id,
        uploader_id=ctx.user.id,
        filename=file.filename or safe_name,
        file_path=str(file_path),
        file_size=len(content),
        status=DocumentStatus.PENDING,
        chunk_size=chunk_size or settings.chunk_size,
        chunk_overlap=chunk_overlap or settings.chunk_overlap,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    background_tasks.add_task(_process_document_task, doc.id)
    return {"id": doc.id, "message": "上传成功，正在解析"}


@router.put("/{doc_id}/replace")
async def replace_document(
    doc_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    ctx: TenantUserContext = Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
):
    """文档更新：删除旧向量后重新切片入库（需求 4.2）。"""
    ensure_tenant_active(ctx.tenant)
    doc = db.query(Document).filter(Document.id == doc_id, Document.tenant_id == ctx.tenant.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == doc.kb_id).first()
    if not kb or not user_can_manage_kb(db, ctx.user, kb):
        raise HTTPException(status_code=403, detail="需要管理权限")
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail="不支持的文件类型")
    content = await file.read()
    check_file_size(ctx.tenant, len(content))
    if os.path.isfile(doc.file_path):
        os.remove(doc.file_path)
    safe_name = f"{uuid.uuid4().hex}{ext}"
    rel_dir = Path(settings.upload_dir) / str(ctx.tenant.id) / str(doc.kb_id)
    rel_dir.mkdir(parents=True, exist_ok=True)
    file_path = rel_dir / safe_name
    file_path.write_bytes(content)
    delete_document_vectors(db, doc)
    doc.filename = file.filename or safe_name
    doc.file_path = str(file_path)
    doc.file_size = len(content)
    doc.status = DocumentStatus.PENDING
    doc.error_message = None
    doc.chunk_size = chunk_size or settings.chunk_size
    doc.chunk_overlap = chunk_overlap or settings.chunk_overlap
    db.commit()
    background_tasks.add_task(_process_document_task, doc.id)
    return {"message": "文档已更新，正在重新解析"}


@router.delete("/{doc_id}")
def delete_document(doc_id: int, ctx: TenantUserContext = Depends(get_current_tenant_user), db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id, Document.tenant_id == ctx.tenant.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == doc.kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    can_delete = doc.uploader_id == ctx.user.id or user_can_manage_kb(db, ctx.user, kb)
    if not can_delete:
        raise HTTPException(status_code=403, detail="无删除权限")
    delete_document_vectors(db, doc)
    if os.path.isfile(doc.file_path):
        os.remove(doc.file_path)
    db.delete(doc)
    db.commit()
    return {"message": "已删除"}


@router.post("/{doc_id}/reparse")
def reparse_document(
    doc_id: int,
    background_tasks: BackgroundTasks,
    ctx: TenantUserContext = Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(Document.id == doc_id, Document.tenant_id == ctx.tenant.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == doc.kb_id).first()
    from app.models.entities import UserRole

    if not kb or not (user_can_manage_kb(db, ctx.user, kb) or ctx.user.role == UserRole.TENANT_ADMIN):
        raise HTTPException(status_code=403, detail="无权限")
    doc.status = DocumentStatus.PENDING
    doc.error_message = None
    db.commit()
    background_tasks.add_task(_process_document_task, doc.id)
    return {"message": "已重新触发解析"}


@router.get("/failed/list")
def failed_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    ctx: TenantUserContext = Depends(require_admin_feature("statistics_dashboard")),
    db: Session = Depends(get_db),
):
    q = db.query(Document).filter(
        Document.tenant_id == ctx.tenant.id,
        Document.status == DocumentStatus.FAILED,
    )
    total = q.count()
    items = q.order_by(Document.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "items": [
            {
                "id": d.id,
                "filename": d.filename,
                "kb_id": d.kb_id,
                "error_message": d.error_message,
            }
            for d in items
        ],
    }
