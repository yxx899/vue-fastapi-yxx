from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import TenantUserContext, get_current_tenant_user
from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_db
from app.models.entities import Tenant, User
from app.schemas.auth import ChangePasswordIn, TenantLoginIn, TenantPolicyOut, UserOut
from app.schemas.common import TokenOut
from app.services.tenant_features import tenant_policy_payload

router = APIRouter(prefix="/auth", tags=["租户认证"])


def _ensure_tenant_ok(tenant: Tenant | None) -> Tenant:
    if not tenant or not tenant.is_active:
        raise HTTPException(status_code=403, detail="租户已禁用")
    if tenant.expires_at and tenant.expires_at < datetime.utcnow():
        raise HTTPException(status_code=403, detail="租户已过期")
    return tenant


def _token_for_user(user: User, tenant: Tenant) -> TokenOut:
    token = create_access_token(
        {"sub": user.id, "type": "tenant", "tenant_id": user.tenant_id, "role": user.role.value}
    )
    return TokenOut(access_token=token)


@router.post("/login", response_model=TokenOut)
def tenant_login(body: TenantLoginIn, db: Session = Depends(get_db)):
    user = (
        db.query(User)
        .filter(User.username == body.username, User.is_active.is_(True))
        .first()
    )
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    _ensure_tenant_ok(tenant)
    return _token_for_user(user, tenant)


@router.get("/me", response_model=UserOut)
def me(ctx: TenantUserContext = Depends(get_current_tenant_user)):
    policy = tenant_policy_payload(ctx.tenant)
    return UserOut(
        id=ctx.user.id,
        username=ctx.user.username,
        display_name=ctx.user.display_name,
        role=ctx.user.role.value,
        tenant_id=ctx.tenant.id,
        tenant_name=ctx.tenant.name,
        tenant_policy=TenantPolicyOut(**policy),
    )


@router.post("/change-password")
def change_password(
    body: ChangePasswordIn,
    ctx: TenantUserContext = Depends(get_current_tenant_user),
    db: Session = Depends(get_db),
):
    if not verify_password(body.old_password, ctx.user.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")
    ctx.user.password_hash = hash_password(body.new_password)
    db.commit()
    return {"message": "密码已更新"}
