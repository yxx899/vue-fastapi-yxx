from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.entities import Document, KnowledgeBase, Tenant, User


def ensure_tenant_active(tenant: Tenant) -> None:
    if not tenant.is_active:
        raise HTTPException(status_code=403, detail="租户已禁用")


def check_kb_quota(db: Session, tenant: Tenant) -> None:
    count = db.query(KnowledgeBase).filter(KnowledgeBase.tenant_id == tenant.id).count()
    if count >= tenant.max_knowledge_bases:
        raise HTTPException(status_code=400, detail="已达知识库数量上限")


def check_document_quota(db: Session, tenant: Tenant) -> None:
    count = db.query(Document).filter(Document.tenant_id == tenant.id).count()
    if count >= tenant.max_documents:
        raise HTTPException(status_code=400, detail="已达文档数量上限")


def check_file_size(tenant: Tenant, size_bytes: int) -> None:
    max_bytes = tenant.max_file_size_mb * 1024 * 1024
    if size_bytes > max_bytes:
        raise HTTPException(status_code=400, detail=f"文件超过 {tenant.max_file_size_mb}MB 限制")


def check_user_quota(db: Session, tenant: Tenant) -> None:
    limit = getattr(tenant, "max_users", 100) or 100
    count = db.query(User).filter(User.tenant_id == tenant.id).count()
    if count >= limit:
        raise HTTPException(status_code=400, detail="已达用户数量上限（由平台配置）")
