from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import TenantUserContext, require_admin_feature
from app.database import get_db
from app.models.entities import Department

router = APIRouter(prefix="/departments", tags=["部门"])


class DeptIn(BaseModel):
    name: str
    parent_id: int | None = None


class DeptOut(BaseModel):
    id: int
    name: str
    parent_id: int | None

    model_config = {"from_attributes": True}


def _build_tree(depts: list[Department]) -> list[dict]:
    nodes = {d.id: {"id": d.id, "name": d.name, "parent_id": d.parent_id, "children": []} for d in depts}
    roots = []
    for d in depts:
        node = nodes[d.id]
        if d.parent_id and d.parent_id in nodes:
            nodes[d.parent_id]["children"].append(node)
        else:
            roots.append(node)
    return roots


@router.get("")
def list_departments(
    tree: bool = False,
    ctx: TenantUserContext = Depends(require_admin_feature("department_management")),
    db: Session = Depends(get_db),
):
    depts = db.query(Department).filter(Department.tenant_id == ctx.tenant.id).order_by(Department.id).all()
    if tree:
        return {"items": _build_tree(depts)}
    return [DeptOut.model_validate(d) for d in depts]


@router.get("/tree")
def department_tree(ctx: TenantUserContext = Depends(require_admin_feature("department_management")), db: Session = Depends(get_db)):
    depts = db.query(Department).filter(Department.tenant_id == ctx.tenant.id).order_by(Department.id).all()
    return {"items": _build_tree(depts)}


@router.post("", response_model=DeptOut)
def create_department(body: DeptIn, ctx: TenantUserContext = Depends(require_admin_feature("department_management")), db: Session = Depends(get_db)):
    dept = Department(tenant_id=ctx.tenant.id, name=body.name, parent_id=body.parent_id)
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept


@router.put("/{dept_id}", response_model=DeptOut)
def update_department(
    dept_id: int,
    body: DeptIn,
    ctx: TenantUserContext = Depends(require_admin_feature("department_management")),
    db: Session = Depends(get_db),
):
    dept = db.query(Department).filter(Department.id == dept_id, Department.tenant_id == ctx.tenant.id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="部门不存在")
    dept.name = body.name
    dept.parent_id = body.parent_id
    db.commit()
    db.refresh(dept)
    return dept


@router.delete("/{dept_id}")
def delete_department(dept_id: int, ctx: TenantUserContext = Depends(require_admin_feature("department_management")), db: Session = Depends(get_db)):
    dept = db.query(Department).filter(Department.id == dept_id, Department.tenant_id == ctx.tenant.id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="部门不存在")
    db.delete(dept)
    db.commit()
    return {"message": "已删除"}
