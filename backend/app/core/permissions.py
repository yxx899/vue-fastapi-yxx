from sqlalchemy.orm import Session

from app.models.entities import (
    KBPermissionType,
    KnowledgeBase,
    KnowledgeBasePermission,
    User,
    UserRole,
)


def user_can_access_kb(db: Session, user: User, kb: KnowledgeBase) -> bool:
    if kb.tenant_id != user.tenant_id:
        return False
    if user.role == UserRole.TENANT_ADMIN:
        return True
    if not kb.is_active:
        return False
    if kb.is_public_in_tenant:
        return True
    q = db.query(KnowledgeBasePermission).filter(
        KnowledgeBasePermission.tenant_id == user.tenant_id,
        KnowledgeBasePermission.kb_id == kb.id,
    )
    perms = q.all()
    for p in perms:
        if p.user_id == user.id:
            return True
        if p.department_id and user.department_id == p.department_id:
            return True
    return False


def user_can_manage_kb(db: Session, user: User, kb: KnowledgeBase) -> bool:
    if kb.tenant_id != user.tenant_id:
        return False
    if user.role == UserRole.TENANT_ADMIN:
        return True
    if not kb.is_active:
        return False
    perms = (
        db.query(KnowledgeBasePermission)
        .filter(
            KnowledgeBasePermission.tenant_id == user.tenant_id,
            KnowledgeBasePermission.kb_id == kb.id,
            KnowledgeBasePermission.permission == KBPermissionType.MANAGE,
        )
        .all()
    )
    for p in perms:
        if p.user_id == user.id:
            return True
        if p.department_id and user.department_id == p.department_id:
            return True
    return False


def list_accessible_kb_ids(db: Session, user: User, *, include_inactive_for_admin: bool = False) -> list[int]:
    from app.models.entities import KnowledgeBase

    q = db.query(KnowledgeBase).filter(KnowledgeBase.tenant_id == user.tenant_id)
    if user.role == UserRole.TENANT_ADMIN and include_inactive_for_admin:
        return [kb.id for kb in q.order_by(KnowledgeBase.id.desc()).all()]
    kbs = q.filter(KnowledgeBase.is_active.is_(True)).all()
    return [kb.id for kb in kbs if user_can_access_kb(db, user, kb)]
