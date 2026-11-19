from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import TenantUserContext, require_admin_feature, require_tenant_admin
from app.core.security import hash_password
from app.database import get_db
from app.models.entities import Department, User, UserRole
from app.services.tenant_limits import check_user_quota

router = APIRouter(prefix="/users", tags=["用户"])


class UserCreateIn(BaseModel):
    username: str
    password: str = Field(min_length=6)
    display_name: str | None = None
    role: UserRole = UserRole.EMPLOYEE
    department_id: int | None = None


class UserUpdateIn(BaseModel):
    display_name: str | None = None
    role: UserRole | None = None
    department_id: int | None = None
    is_active: bool | None = None


class UserItemOut(BaseModel):
    id: int
    username: str
    display_name: str | None
    role: str
    department_id: int | None
    is_active: bool

    model_config = {"from_attributes": True}


@router.get("")
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    ctx: TenantUserContext = Depends(require_admin_feature("user_management")),
    db: Session = Depends(get_db),
):
    q = db.query(User).filter(User.tenant_id == ctx.tenant.id)
    total = q.count()
    items = q.order_by(User.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "items": [
            UserItemOut(
                id=u.id,
                username=u.username,
                display_name=u.display_name,
                role=u.role.value,
                department_id=u.department_id,
                is_active=u.is_active,
            )
            for u in items
        ],
    }


@router.post("", response_model=UserItemOut)
def create_user(
    body: UserCreateIn,
    ctx: TenantUserContext = Depends(require_admin_feature("user_management")),
    db: Session = Depends(get_db),
):
    check_user_quota(db, ctx.tenant)
    exists = (
        db.query(User)
        .filter(User.tenant_id == ctx.tenant.id, User.username == body.username)
        .first()
    )
    if exists:
        raise HTTPException(status_code=400, detail="用户名已存在")
    if body.department_id is not None:
        dept = (
            db.query(Department)
            .filter(Department.id == body.department_id, Department.tenant_id == ctx.tenant.id)
            .first()
        )
        if not dept:
            raise HTTPException(status_code=400, detail="部门不存在或不属于本企业")
    user = User(
        tenant_id=ctx.tenant.id,
        username=body.username,
        password_hash=hash_password(body.password),
        display_name=body.display_name,
        role=body.role,
        department_id=body.department_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserItemOut(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        role=user.role.value,
        department_id=user.department_id,
        is_active=user.is_active,
    )


@router.put("/{user_id}", response_model=UserItemOut)
def update_user(
    user_id: int,
    body: UserUpdateIn,
    ctx: TenantUserContext = Depends(require_admin_feature("user_management")),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id, User.tenant_id == ctx.tenant.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    data = body.model_dump(exclude_unset=True)
    if "department_id" in data and data["department_id"] is not None:
        dept = (
            db.query(Department)
            .filter(Department.id == data["department_id"], Department.tenant_id == ctx.tenant.id)
            .first()
        )
        if not dept:
            raise HTTPException(status_code=400, detail="部门不存在或不属于本企业")
    for k, v in data.items():
        setattr(user, k, v)
    db.commit()
    db.refresh(user)
    return UserItemOut(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        role=user.role.value,
        department_id=user.department_id,
        is_active=user.is_active,
    )


class ResetPasswordIn(BaseModel):
    password: str = Field(min_length=6)


@router.post("/{user_id}/reset-password")
def reset_password(
    user_id: int,
    body: ResetPasswordIn,
    ctx: TenantUserContext = Depends(require_admin_feature("user_management")),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id, User.tenant_id == ctx.tenant.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.password_hash = hash_password(body.password)
    db.commit()
    return {"message": "密码已重置"}


@router.delete("/{user_id}")
def delete_user(user_id: int, ctx: TenantUserContext = Depends(require_tenant_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id, User.tenant_id == ctx.tenant.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == ctx.user.id:
        raise HTTPException(status_code=400, detail="不能删除当前登录用户")
    db.delete(user)
    db.commit()
    return {"message": "已删除"}
