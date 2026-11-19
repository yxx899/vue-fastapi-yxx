from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import safe_decode_token, subject_id
from app.services.tenant_features import ensure_tenant_feature
from app.database import get_db
from app.models.entities import PlatformAdmin, Tenant, User

security = HTTPBearer(auto_error=False)


class TenantUserContext:
    def __init__(self, user: User, tenant: Tenant):
        self.user = user
        self.tenant = tenant


class PlatformContext:
    def __init__(self, admin: PlatformAdmin):
        self.admin = admin


def get_current_tenant_user(
    creds: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> TenantUserContext:
    if not creds or not creds.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    payload = safe_decode_token(creds.credentials)
    if not payload or payload.get("type") != "tenant":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效令牌")
    uid = subject_id(payload)
    if uid is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效令牌")
    user = db.query(User).filter(User.id == uid, User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    from datetime import datetime

    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    if not tenant or not tenant.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="租户已禁用")
    if tenant.expires_at and tenant.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="租户已过期")
    return TenantUserContext(user=user, tenant=tenant)


def require_tenant_admin(ctx: TenantUserContext = Depends(get_current_tenant_user)) -> TenantUserContext:
    from app.models.entities import UserRole

    if ctx.user.role != UserRole.TENANT_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要租户管理员权限")
    return ctx


def require_admin_feature(feature: str):
    """租户管理员 + 平台已为该租户开启的功能。"""

    def _dep(ctx: TenantUserContext = Depends(require_tenant_admin)) -> TenantUserContext:
        ensure_tenant_feature(ctx.tenant, feature)
        return ctx

    return _dep


def get_platform_admin(
    creds: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> PlatformContext:
    if not creds or not creds.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    payload = safe_decode_token(creds.credentials)
    if not payload or payload.get("type") != "platform":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效令牌")
    aid = subject_id(payload)
    if aid is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效令牌")
    admin = db.query(PlatformAdmin).filter(PlatformAdmin.id == aid, PlatformAdmin.is_active.is_(True)).first()
    if not admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="管理员不存在")
    return PlatformContext(admin=admin)
