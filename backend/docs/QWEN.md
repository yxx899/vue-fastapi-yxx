# 通义千问（DashScope）接入说明

本项目 RAG 问答使用 **阿里云百炼 / DashScope** 通义千问生成回答。

## 1. 推荐：API 快速接入（工作空间密钥）

控制台「API 快速接入」弹窗会给出：

- `sk-ws-...` 密钥
- 工作空间主机，例如 `ws-xxxx.cn-beijing.maas.aliyuncs.com`
- DashScope 地址：`https://ws-xxxx.cn-beijing.maas.aliyuncs.com/api/v1`

写入 `backend/.env`：

```env
DASHSCOPE_API_KEY=sk-ws-你的密钥
DASHSCOPE_WORKSPACE=ws-xxxx
DASHSCOPE_REGION=cn-beijing
DASHSCOPE_BASE_URL=https://ws-xxxx.cn-beijing.maas.aliyuncs.com/api/v1
QWEN_MODEL=qwen-plus
```

> 工作空间内模型名可能与全局不同。本环境已验证 `qwen-plus` 可用；若报 Model not exist，在控制台查看已开通模型后改 `QWEN_MODEL`。

## 2. 本地自检

```bash
cd backend
.\.venv\Scripts\python.exe scripts\test_qwen.py
```

或：`GET http://127.0.0.1:8000/api/health/qwen`，`"ok": true` 表示可用。

## 3. 与 RAG 的关系

1. 文档分块写入 Chroma  
2. 用户提问 → 检索相关片段（无关则礼貌拒答）  
3. 有相关片段时，由 **通义千问** 根据上下文生成答案  
4. 千问不可用时降级为知识库摘录整理  

## 4. 配置项

| 变量 | 说明 |
|------|------|
| `DASHSCOPE_API_KEY` | 必填 |
| `DASHSCOPE_WORKSPACE` | 工作空间 ID（`ws-` 开头） |
| `DASHSCOPE_REGION` | 默认 `cn-beijing` |
| `DASHSCOPE_BASE_URL` | 可选专属 `/api/v1` 网关 |
| `QWEN_MODEL` | 默认 `qwen-plus` |
