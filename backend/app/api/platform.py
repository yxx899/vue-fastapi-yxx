import os
import shutil
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import PlatformContext, get_platform_admin
from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_db
from app.models.entities import (
    ChatMessage,
    ChatSession,
    Department,
    Document,
    DocumentChunk,
    KnowledgeBase,
    KnowledgeBasePermission,
    PlatformAdmin,
    QALog,
    Tenant,
    User,
)
from app.schemas.auth import PlatformLoginIn
from app.schemas.common import TokenOut
from app.services.document_pipeline import delete_document_vectors
from app.services.tenant_features import (
    DEFAULT_TENANT_FEATURES,
    serialize_tenant_features,
    tenant_features,
    tenant_policy_payload,
)

router = APIRouter(prefix="/platform", tags=["平台管理"])


class TenantCreateIn(BaseModel):
    name: str
    contact_name: str | None = None
    contact_phone: str | None = None
    max_knowledge_bases: int = 10
    max_documents: int = 1000
    max_file_size_mb: int = 50
    max_users: int = 100
    features: dict[str, bool] | None = None
    expires_at: datetime | None = None
    admin_username: str = Field(default="admin")
    admin_password: str = Field(default="admin123", min_length=6)


class TenantUpdateIn(BaseModel):
    name: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    max_knowledge_bases: int | None = None
    max_documents: int | None = None
    max_file_size_mb: int | None = None
    max_users: int | None = None
    features: dict[str, bool] | None = None
    expires_at: datetime | None = None
    is_active: bool | None = None


class TenantOut(BaseModel):
    id: int
    name: str
    contact_name: str | None
    contact_phone: str | None
    max_knowledge_bases: int
    max_documents: int
    max_file_size_mb: int
    max_users: int = 100
    features: dict[str, bool] = Field(default_factory=lambda: dict(DEFAULT_TENANT_FEATURES))
    is_active: bool
    expires_at: datetime | None

    model_config = {"from_attributes": True}


def _tenant_row(t: Tenant) -> dict:
    row = TenantOut.model_validate(t).model_dump()
    row["features"] = tenant_features(t)
    row["max_users"] = getattr(t, "max_users", 100) or 100
    return row


@router.post("/auth/login", response_model=TokenOut)
def platform_login(body: PlatformLoginIn, db: Session = Depends(get_db)):
    admin = db.query(PlatformAdmin).filter(PlatformAdmin.username == body.username).first()
    if not admin or not verify_password(body.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_access_token({"sub": admin.id, "type": "platform"})
    return TokenOut(access_token=token)


@router.get("/tenants")
def list_tenants(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    _: PlatformContext = Depends(get_platform_admin),
    db: Session = Depends(get_db),
):
    q = db.query(Tenant)
    if keyword:
        q = q.filter(Tenant.name.contains(keyword))
    total = q.count()
    items = q.order_by(Tenant.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    out_items = []
    for t in items:
        row = _tenant_row(t)
        row["user_count"] = db.query(User).filter(User.tenant_id == t.id).count()
        row["kb_count"] = db.query(KnowledgeBase).filter(KnowledgeBase.tenant_id == t.id).count()
        row["document_count"] = db.query(Document).filter(Document.tenant_id == t.id).count()
        row["qa_count"] = db.query(QALog).filter(QALog.tenant_id == t.id).count()
        out_items.append(row)
    return {"total": total, "items": out_items}


@router.post("/tenants", response_model=TenantOut)
def create_tenant(body: TenantCreateIn, _: PlatformContext = Depends(get_platform_admin), db: Session = Depends(get_db)):
    from app.models.entities import UserRole

    tenant = Tenant(
        name=body.name,
        contact_name=body.contact_name,
        contact_phone=body.contact_phone,
        max_knowledge_bases=body.max_knowledge_bases,
        max_documents=body.max_documents,
        max_file_size_mb=body.max_file_size_mb,
        max_users=body.max_users,
        features_json=serialize_tenant_features(body.features or DEFAULT_TENANT_FEATURES),
        expires_at=body.expires_at,
    )
    db.add(tenant)
    db.flush()
    admin_user = User(
        tenant_id=tenant.id,
        username=body.admin_username,
        password_hash=hash_password(body.admin_password),
        display_name="租户管理员",
        role=UserRole.TENANT_ADMIN,
    )
    db.add(admin_user)
    db.commit()
    db.refresh(tenant)
    return tenant


@router.put("/tenants/{tenant_id}", response_model=TenantOut)
def update_tenant(
    tenant_id: int,
    body: TenantUpdateIn,
    _: PlatformContext = Depends(get_platform_admin),
    db: Session = Depends(get_db),
):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")
    data = body.model_dump(exclude_unset=True)
    features = data.pop("features", None)
    for k, v in data.items():
        setattr(tenant, k, v)
    if features is not None:
        tenant.features_json = serialize_tenant_features(features)
    db.commit()
    db.refresh(tenant)
    return tenant


class TenantFeaturesPatchIn(BaseModel):
    features: dict[str, bool]


@router.patch("/tenants/{tenant_id}/features")
def patch_tenant_features(
    tenant_id: int,
    body: TenantFeaturesPatchIn,
    _: PlatformContext = Depends(get_platform_admin),
    db: Session = Depends(get_db),
):
    """仅更新功能开关（列表内直接切换时使用）。"""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")
    merged = tenant_features(tenant)
    merged.update({k: bool(v) for k, v in body.features.items() if k in DEFAULT_TENANT_FEATURES})
    tenant.features_json = serialize_tenant_features(merged)
    db.commit()
    db.refresh(tenant)
    return {"tenant_id": tenant.id, "features": tenant_features(tenant)}


@router.delete("/tenants/{tenant_id}")
def delete_tenant(
    tenant_id: int,
    _: PlatformContext = Depends(get_platform_admin),
    db: Session = Depends(get_db),
):
    """永久删除租户及其用户、知识库、文档、向量、会话与审计数据。"""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")

    tid = tenant.id
    name = tenant.name
    docs = db.query(Document).filter(Document.tenant_id == tid).all()
    for doc in docs:
        try:
            delete_document_vectors(db, doc)
        except Exception:
            pass
        if doc.file_path and os.path.isfile(doc.file_path):
            try:
                os.remove(doc.file_path)
            except OSError:
                pass

    session_ids = [
        sid for (sid,) in db.query(ChatSession.id).filter(ChatSession.tenant_id == tid).all()
    ]
    if session_ids:
        db.query(ChatMessage).filter(ChatMessage.session_id.in_(session_ids)).delete(
            synchronize_session=False
        )
    db.query(ChatSession).filter(ChatSession.tenant_id == tid).delete(synchronize_session=False)
    db.query(QALog).filter(QALog.tenant_id == tid).delete(synchronize_session=False)
    db.query(KnowledgeBasePermission).filter(KnowledgeBasePermission.tenant_id == tid).delete(
        synchronize_session=False
    )

    doc_ids = [d.id for d in docs]
    if doc_ids:
        db.query(DocumentChunk).filter(DocumentChunk.document_id.in_(doc_ids)).delete(
            synchronize_session=False
        )
    db.query(Document).filter(Document.tenant_id == tid).delete(synchronize_session=False)
    db.query(KnowledgeBase).filter(KnowledgeBase.tenant_id == tid).delete(synchronize_session=False)

    db.query(User).filter(User.tenant_id == tid).update(
        {User.department_id: None}, synchronize_session=False
    )
    db.query(Department).filter(Department.tenant_id == tid).update(
        {Department.parent_id: None}, synchronize_session=False
    )
    db.query(Department).filter(Department.tenant_id == tid).delete(synchronize_session=False)
    db.query(User).filter(User.tenant_id == tid).delete(synchronize_session=False)
    db.delete(tenant)
    db.commit()

    upload_root = Path(settings.upload_dir) / str(tid)
    if upload_root.is_dir():
        shutil.rmtree(upload_root, ignore_errors=True)

    return {"message": "租户已删除", "id": tid, "name": name}


@router.get("/tenants/{tenant_id}/policy")
def get_tenant_policy(
    tenant_id: int,
    _: PlatformContext = Depends(get_platform_admin),
    db: Session = Depends(get_db),
):
    """查看某租户的配额与功能开关（与租户侧 /auth/me 中 tenant_policy 一致）。"""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")
    return {"tenant_id": tenant.id, "tenant_name": tenant.name, **tenant_policy_payload(tenant)}


@router.get("/stats/overview")
def platform_stats(_: PlatformContext = Depends(get_platform_admin), db: Session = Depends(get_db)):
    return {
        "tenant_count": db.query(Tenant).count(),
        "active_tenant_count": db.query(Tenant).filter(Tenant.is_active.is_(True)).count(),
        "user_count": db.query(User).count(),
        "kb_count": db.query(KnowledgeBase).count(),
        "document_count": db.query(Document).count(),
        "qa_count": db.query(QALog).count(),
    }


def _tenant_stat_rows(db: Session, tenants: list[Tenant]) -> list[dict]:
    rows = []
    for t in tenants:
        rows.append(
            {
                "tenant_id": t.id,
                "tenant_name": t.name,
                "is_active": t.is_active,
                "contact_name": t.contact_name,
                "contact_phone": t.contact_phone,
                "expires_at": t.expires_at.isoformat() if t.expires_at else None,
                "user_count": db.query(User).filter(User.tenant_id == t.id).count(),
                "kb_count": db.query(KnowledgeBase).filter(KnowledgeBase.tenant_id == t.id).count(),
                "document_count": db.query(Document).filter(Document.tenant_id == t.id).count(),
                "qa_count": db.query(QALog).filter(QALog.tenant_id == t.id).count(),
            }
        )
    return rows


@router.get("/stats/by-tenant")
def platform_stats_by_tenant(
    active_only: bool | None = None,
    _: PlatformContext = Depends(get_platform_admin),
    db: Session = Depends(get_db),
):
    """平台级各租户汇总（仅元数据与计数，不含文档/对话正文）。"""
    q = db.query(Tenant).order_by(Tenant.id.desc())
    if active_only is True:
        q = q.filter(Tenant.is_active.is_(True))
    elif active_only is False:
        q = q.filter(Tenant.is_active.is_(False))
    tenants = q.all()
    return {"total": len(tenants), "items": _tenant_stat_rows(db, tenants)}
