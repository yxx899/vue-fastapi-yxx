"""初始化或重置平台超管（默认 platform / platform123）"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.security import hash_password
from app.database import Base, SessionLocal, engine
from app.models.entities import PlatformAdmin


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset-password", action="store_true", help="重置 platform 密码为 platform123")
    parser.add_argument("--username", default="platform")
    parser.add_argument("--password", default="platform123", help="新建账号时的密码（至少6位）")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        admin = db.query(PlatformAdmin).filter(PlatformAdmin.username == args.username).first()
        if not admin:
            if len(args.password) < 6:
                print("密码至少 6 位")
                return 1
            db.add(
                PlatformAdmin(
                    username=args.username,
                    password_hash=hash_password(args.password),
                    is_active=True,
                )
            )
            db.commit()
            print(f"已创建平台超管：{args.username} / {args.password}")
            return 0
        if args.reset_password or args.password != "platform123":
            pwd = "platform123" if args.reset_password else args.password
            if len(pwd) < 6:
                print("密码至少 6 位")
                return 1
            admin.password_hash = hash_password(pwd)
            admin.is_active = True
            db.commit()
            print(f"已重置平台超管 {args.username} 密码为 {pwd}")
        else:
            print(f"平台超管 {args.username} 已存在；加 --reset-password 重置为 platform123")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main() or 0)
