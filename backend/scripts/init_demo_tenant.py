"""创建演示租户：demo / admin123"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.security import hash_password
from app.database import Base, SessionLocal, engine
from app.models.entities import KnowledgeBase, Tenant, User, UserRole


def _parse_args():
    p = argparse.ArgumentParser(description="初始化演示租户")
    p.add_argument("--reset-password", action="store_true", help="重置 admin 密码为 admin123")
    return p.parse_args()


def main():
    args = _parse_args()
    from app.config import settings

    if settings.database_url.startswith("sqlite"):
        db_path = settings.database_url.replace("sqlite:///", "")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.query(Tenant).filter(Tenant.name == "演示企业").first()
        if existing:
            admin = db.query(User).filter(User.tenant_id == existing.id, User.username == "admin").first()
            if admin and args.reset_password:
                admin.password_hash = hash_password("admin123")
                db.commit()
                print("已重置演示租户 admin 密码为 admin123")
            if db.query(KnowledgeBase).filter(KnowledgeBase.tenant_id == existing.id).count() == 0:
                db.add(
                    KnowledgeBase(
                        tenant_id=existing.id,
                        name="公司产品手册",
                        description="演示知识库，可上传 PDF/Markdown/Word 文档",
                        is_public_in_tenant=True,
                    )
                )
                db.commit()
                print("已为演示租户补充默认知识库")
            else:
                print("演示租户已存在")
            return
        tenant = Tenant(name="演示企业", contact_name="张三", contact_phone="13800000000")
        db.add(tenant)
        db.flush()
        db.add(
            User(
                tenant_id=tenant.id,
                username="admin",
                password_hash=hash_password("admin123"),
                display_name="租户管理员",
                role=UserRole.TENANT_ADMIN,
            )
        )
        db.add(
            User(
                tenant_id=tenant.id,
                username="employee",
                password_hash=hash_password("employee123"),
                display_name="普通员工",
                role=UserRole.EMPLOYEE,
            )
        )
        db.add(
            KnowledgeBase(
                tenant_id=tenant.id,
                name="公司产品手册",
                description="演示知识库，可上传 PDF/Markdown/Word 文档",
                is_public_in_tenant=True,
            )
        )
        db.commit()
        print("演示租户创建成功：登录用户名 admin / admin123 或 employee / employee123")
    finally:
        db.close()


if __name__ == "__main__":
    main()
