from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import audit, auth, chat, departments, documents, knowledge_bases, platform, users
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models.entities import PlatformAdmin
from app.core.security import hash_password


def seed_platform_admin():
    db = SessionLocal()
    try:
        if not db.query(PlatformAdmin).first():
            db.add(
                PlatformAdmin(
                    username="platform",
                    password_hash=hash_password("platform123"),
                )
            )
            db.commit()
    finally:
        db.close()


def _migrate_tenant_columns():
    """SQLite 等无 Alembic 时补列，避免旧库缺字段。"""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if "tenants" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("tenants")}
    with engine.begin() as conn:
        if "max_users" not in cols:
            conn.execute(text("ALTER TABLE tenants ADD COLUMN max_users INTEGER DEFAULT 100"))
        if "features_json" not in cols:
            conn.execute(text("ALTER TABLE tenants ADD COLUMN features_json TEXT"))


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    _migrate_tenant_columns()
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.chroma_persist_dir).mkdir(parents=True, exist_ok=True)
    seed_platform_admin()
    yield


app = FastAPI(title="企业多租户智能知识库", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(platform.router, prefix="/api")
app.include_router(departments.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(knowledge_bases.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(audit.router, prefix="/api")


@app.get("/api/health")
def health():
    db_kind = "postgresql" if settings.database_url.startswith("postgresql") else "sqlite"
    return {"status": "ok", "db": db_kind}


@app.get("/api/health/qwen")
def health_qwen():
    from app.services.qwen_client import probe_qwen

    return probe_qwen()
