# 企业多租户内部智能知识库系统

对齐需求文档：**FastAPI + SQLAlchemy + Pydantic + LangChain/LangGraph + 通义千问 + BGE + Chroma + Vue3 + Element Plus + MySQL**

## 需求功能对照（必选）

| 模块 | 需求要点 | 实现位置 |
|------|----------|----------|
| 平台超管 | 独立登录、租户 CRUD、配额、**功能开关**、启停、过期时间、全平台统计（不看租户业务内容） | `/platform/*` |
| 租户管理员 | 用户/部门/RBAC、知识库、审计导出、看板、解析失败重试 | `/app/admin/*` |
| 普通员工 | 改密、可见知识库、按权限上传/删文档、多库 SSE 问答、溯源、赞踩、会话管理 | `/app/chat`、`/app/kbs` |
| 多租户隔离 | 业务表 `tenant_id`；Chroma 元数据 `tenant_id+kb_id` 强制过滤 | `vector_store.py`、`permissions.py` |
| 文档 | PDF/MD/TXT/Word、异步解析、分块参数可调、vector_id 映射、更新=删向量再入库 | `document_pipeline.py`、`/documents/*` |
| RAG | LangGraph 编排检索→Prompt→Qwen SSE；断连检测 | `rag_graph.py`、`/chat/stream` |
| 安全 | JWT、bcrypt、禁止前端传 tenant_id、上传后缀白名单 | `deps.py`、`auth.py` |

可选扩展（第 5 章）未默认开启：Reranker、Prompt 模板管理、批量压缩包、版本管理、向量备份、敏感词。

## 快速启动

### 1. 数据库

**MySQL（需求文档默认）**

```bash
docker compose up -d mysql
```

`backend/.env`：

`DATABASE_URL=mysql+pymysql://kb:kb123456@localhost:3306/knowledge_base?charset=utf8mb4`

**SQLite / PostgreSQL**：见 `backend/.env.example`

### 2. 后端

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python scripts/init_demo_tenant.py
uvicorn app.main:app --reload --port 8000
```

### 3. 前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173

## 默认账号

| 入口 | 账号 | 密码 |
|------|------|------|
| 平台超管 `/platform/login` | platform | platform123 |
| 租户 `/login` | admin | admin123 |
| 员工 | employee | employee123 |

## AI

- `DASHSCOPE_API_KEY`：通义千问（配置与自检见 [backend/docs/QWEN.md](backend/docs/QWEN.md)，运行 `python backend/scripts/test_qwen.py`）
- `EMBEDDING_MOCK=false` + `sentence-transformers`：BGE 向量（默认 mock 便于本地跑通）

## 向量库说明

本项目采用 **Chroma 持久化向量库**（演示/开发）。生产可替换 Milvus/FAISS（见需求 4.2）。

## API 文档

http://127.0.0.1:8000/docs

## 冒烟测试

后端需先启动（仅保留**一个**占用 8000 的 uvicorn 进程，多开会导致接口版本不一致）：

```bash
cd backend
.venv\Scripts\python.exe scripts\test_all_api.py
```

若租户 `admin` 无法登录（改过密码），可恢复演示密码：

```bash
python scripts/init_demo_tenant.py --reset-password
```
