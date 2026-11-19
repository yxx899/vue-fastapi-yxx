from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import TenantUserContext, get_current_tenant_user, require_tenant_admin
from app.core.permissions import list_accessible_kb_ids, user_can_access_kb, user_can_manage_kb
from app.database import get_db
from app.models.entities import Document, KBPermissionType, KnowledgeBase, KnowledgeBasePermission, UserRole
from app.services.document_pipeline import delete_document_vectors
from app.services.tenant_features import ensure_tenant_feature
from app.services.tenant_limits import check_kb_quota, ensure_tenant_active
router = APIRouter(prefix="/knowledge-bases", tags=["知识库"])


class KBIn(BaseModel):
    name: str
    description: str | None = None
    is_public_in_tenant: bool = False


class KBOut(BaseModel):
    id: int
    name: str
    description: str | None
    is_public_in_tenant: bool
    is_active: bool
    can_manage: bool = False

    model_config = {"from_attributes": True}


class PermissionIn(BaseModel):
    user_id: int | None = None
    department_id: int | None = None
    permission: KBPermissionType


@router.get("")
def list_kbs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    ctx: TenantUserContext = Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
):
    ensure_tenant_feature(ctx.tenant, "knowledge_base")
    ids = list_accessible_kb_ids(db, ctx.user, include_inactive_for_admin=True)
    q = db.query(KnowledgeBase).filter(KnowledgeBase.id.in_(ids))
    total = q.count()
    items = q.order_by(KnowledgeBase.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    out = []
    for kb in items:
        out.append(
            KBOut(
                id=kb.id,
                name=kb.name,
                description=kb.description,
                is_public_in_tenant=kb.is_public_in_tenant,
                is_active=kb.is_active,
                can_manage=user_can_manage_kb(db, ctx.user, kb),
            )
        )
    return {"total": total, "items": out}


@router.post("", response_model=KBOut)
def create_kb(body: KBIn, ctx: TenantUserContext = Depends(require_tenant_admin), db: Session = Depends(get_db)):
    ensure_tenant_active(ctx.tenant)
    ensure_tenant_feature(ctx.tenant, "knowledge_base")
    check_kb_quota(db, ctx.tenant)
    kb = KnowledgeBase(
        tenant_id=ctx.tenant.id,
        name=body.name,
        description=body.description,
        is_public_in_tenant=body.is_public_in_tenant,
    )
    db.add(kb)
    db.commit()
    db.refresh(kb)
    return KBOut(
        id=kb.id,
        name=kb.name,
        description=kb.description,
        is_public_in_tenant=kb.is_public_in_tenant,
        is_active=kb.is_active,
        can_manage=True,
    )


@router.put("/{kb_id}", response_model=KBOut)
def update_kb(
    kb_id: int,
    body: KBIn,
    ctx: TenantUserContext = Depends(require_tenant_admin),
    db: Session = Depends(get_db),
):
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id, KnowledgeBase.tenant_id == ctx.tenant.id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    kb.name = body.name
    kb.description = body.description
    kb.is_public_in_tenant = body.is_public_in_tenant
    db.commit()
    db.refresh(kb)
    return KBOut(
        id=kb.id,
        name=kb.name,
        description=kb.description,
        is_public_in_tenant=kb.is_public_in_tenant,
        is_active=kb.is_active,
        can_manage=True,
    )


@router.post("/{kb_id}/toggle")
def toggle_kb(kb_id: int, active: bool, ctx: TenantUserContext = Depends(require_tenant_admin), db: Session = Depends(get_db)):
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id, KnowledgeBase.tenant_id == ctx.tenant.id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    kb.is_active = active
    db.commit()
    return {"message": "ok", "is_active": kb.is_active}


@router.delete("/{kb_id}")
def delete_kb(kb_id: int, ctx: TenantUserContext = Depends(require_tenant_admin), db: Session = Depends(get_db)):
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id, KnowledgeBase.tenant_id == ctx.tenant.id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    docs = db.query(Document).filter(Document.kb_id == kb.id).all()
    for doc in docs:
        delete_document_vectors(db, doc)
        db.delete(doc)
    db.query(KnowledgeBasePermission).filter(KnowledgeBasePermission.kb_id == kb.id).delete()
    db.delete(kb)
    db.commit()
    return {"message": "知识库已删除"}


def _ensure_kb_manage(db: Session, ctx: TenantUserContext, kb_id: int) -> KnowledgeBase:
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id, KnowledgeBase.tenant_id == ctx.tenant.id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    if not user_can_manage_kb(db, ctx.user, kb):
        raise HTTPException(status_code=403, detail="需要该知识库的管理权限")
    return kb


@router.get("/{kb_id}/permissions")
def list_permissions(kb_id: int, ctx: TenantUserContext = Depends(get_current_tenant_user), db: Session = Depends(get_db)):
    _ensure_kb_manage(db, ctx, kb_id)
    perms = db.query(KnowledgeBasePermission).filter(KnowledgeBasePermission.kb_id == kb_id).all()
    return [
        {
            "id": p.id,
            "user_id": p.user_id,
            "department_id": p.department_id,
            "permission": p.permission.value,
        }
        for p in perms
    ]


@router.post("/{kb_id}/permissions")
def add_permission(
    kb_id: int,
    body: PermissionIn,
    ctx: TenantUserContext = Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
):
    _ensure_kb_manage(db, ctx, kb_id)
    if not body.user_id and not body.department_id:
        raise HTTPException(status_code=400, detail="需指定 user_id 或 department_id")
    perm = KnowledgeBasePermission(
        tenant_id=ctx.tenant.id,
        kb_id=kb_id,
        user_id=body.user_id,
        department_id=body.department_id,
        permission=body.permission,
    )
    db.add(perm)
    db.commit()
    return {"message": "已添加"}


@router.delete("/permissions/{perm_id}")
def remove_permission(perm_id: int, ctx: TenantUserContext = Depends(get_current_tenant_user), db: Session = Depends(get_db)):
    perm = (
        db.query(KnowledgeBasePermission)
        .filter(KnowledgeBasePermission.id == perm_id, KnowledgeBasePermission.tenant_id == ctx.tenant.id)
        .first()
    )
    if not perm:
        raise HTTPException(status_code=404, detail="权限记录不存在")
    _ensure_kb_manage(db, ctx, perm.kb_id)
    db.delete(perm)
    db.commit()
    return {"message": "已删除"}


def _get_kb_or_403(db: Session, ctx: TenantUserContext, kb_id: int, manage: bool = False) -> KnowledgeBase:
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id, KnowledgeBase.tenant_id == ctx.tenant.id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    ok = user_can_manage_kb(db, ctx.user, kb) if manage else user_can_access_kb(db, ctx.user, kb)
    if not ok:
        raise HTTPException(status_code=403, detail="无权限访问该知识库")
    return kb
