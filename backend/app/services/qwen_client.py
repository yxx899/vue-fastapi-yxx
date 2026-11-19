"""通义千问（DashScope）调用封装 — 使用官方 dashscope 2.x Client。"""
from __future__ import annotations

import time
from collections.abc import Iterator
from typing import Any

from app.config import settings

_client = None


def _messages_for_api(messages: list[dict]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for m in messages:
        role = m.get("role") or "user"
        content = m.get("content")
        if content is None:
            continue
        out.append({"role": role, "content": str(content)})
    return out


def get_client():
    global _client
    if _client is None:
        import dashscope

        if not settings.dashscope_api_key:
            raise ValueError("未配置 DASHSCOPE_API_KEY")
        kwargs: dict[str, Any] = {"api_key": settings.dashscope_api_key}
        if settings.dashscope_base_url:
            kwargs["base_url"] = settings.dashscope_base_url.rstrip("/")
        else:
            if settings.dashscope_workspace:
                kwargs["workspace"] = settings.dashscope_workspace
            if settings.dashscope_region:
                kwargs["region"] = settings.dashscope_region
        _client = dashscope.Client(**kwargs)
    return _client


def reset_client() -> None:
    global _client
    _client = None


def qwen_http_enabled() -> bool:
    key = settings.dashscope_api_key
    if not key:
        return False
    # 已配置工作空间或专属网关时，允许 sk-ws- 密钥
    if settings.dashscope_workspace or settings.dashscope_base_url:
        return True
    if settings.qwen_skip_ws_key and key.startswith("sk-ws-"):
        return False
    return True


def qwen_skip_reason() -> str | None:
    key = settings.dashscope_api_key
    if not key:
        return "未配置 DASHSCOPE_API_KEY"
    if (
        settings.qwen_skip_ws_key
        and key.startswith("sk-ws-")
        and not settings.dashscope_workspace
        and not settings.dashscope_base_url
    ):
        return (
            "当前为 sk-ws- 密钥且未配置工作空间。请在 .env 填写 DASHSCOPE_WORKSPACE"
            "（如 ws-xxxx），或改用百炼「API-KEY 管理」中的 sk- 密钥。"
        )
    return None


def _is_rate_limit(exc: BaseException) -> bool:
    name = type(exc).__name__.lower()
    if "ratelimit" in name or "throttl" in name:
        return True
    msg = str(exc).lower()
    return "rate limit" in msg or "limit_requests" in msg or "429" in msg


def _format_api_error(exc: BaseException) -> str:
    if _is_rate_limit(exc):
        return (
            "通义千问请求频率或配额已达上限（429）。请在阿里云百炼控制台查看用量与配额，"
            "稍后再试；或确认已配置 DASHSCOPE_WORKSPACE / 专属网关地址。"
        )
    return f"通义千问调用失败：{exc}"


def chat_complete(messages: list[dict], *, model: str | None = None) -> str:
    """非流式调用，带限流重试。"""
    client = get_client()
    model = model or settings.qwen_model
    api_messages = _messages_for_api(messages)
    last_exc: BaseException | None = None
    for attempt, delay in enumerate((0, 2, 5, 12)):
        if delay:
            time.sleep(delay)
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=api_messages,
                stream=False,
            )
            if not resp.choices:
                raise RuntimeError("模型返回为空")
            text = (resp.choices[0].message.content or "").strip()
            if not text:
                raise RuntimeError("模型返回内容为空")
            return text
        except Exception as e:
            last_exc = e
            if not _is_rate_limit(e) or attempt >= 3:
                break
    raise RuntimeError(_format_api_error(last_exc or RuntimeError("未知错误")))


def stream_chat(messages: list[dict], *, model: str | None = None) -> Iterator[str]:
    """流式输出文本片段；失败时抛出 RuntimeError（含友好说明）。"""
    client = get_client()
    model = model or settings.qwen_model
    api_messages = _messages_for_api(messages)
    last_exc: BaseException | None = None
    for attempt, delay in enumerate((0, 2, 5)):
        if delay:
            time.sleep(delay)
        try:
            stream = client.chat.completions.create(
                model=model,
                messages=api_messages,
                stream=True,
            )
            got = False
            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                piece = getattr(delta, "content", None) if delta else None
                if piece:
                    got = True
                    yield piece
            if got:
                return
            raise RuntimeError("模型流式返回为空")
        except Exception as e:
            last_exc = e
            if not _is_rate_limit(e) or attempt >= 2:
                break
    raise RuntimeError(_format_api_error(last_exc or RuntimeError("未知错误")))


def probe_qwen() -> dict[str, Any]:
    """供 /api/health/qwen 检测密钥与连通性。"""
    key = settings.dashscope_api_key or ""
    info: dict[str, Any] = {
        "configured": bool(key),
        "model": settings.qwen_model,
        "workspace": settings.dashscope_workspace or "",
        "region": settings.dashscope_region or "",
        "key_hint": f"{key[:8]}…" if len(key) > 8 else "",
        "key_type": "workspace(sk-ws-)" if key.startswith("sk-ws-") else "standard",
    }
    skip = qwen_skip_reason()
    if skip:
        info["ok"] = False
        info["message"] = skip
        return info
    if not key:
        info["ok"] = False
        info["message"] = "未配置 DASHSCOPE_API_KEY"
        return info
    try:
        reset_client()
        text = chat_complete([{"role": "user", "content": "回复：OK"}], model=settings.qwen_model)
        info["ok"] = True
        info["message"] = "通义千问可用"
        info["sample"] = text[:80]
    except Exception as e:
        info["ok"] = False
        info["message"] = _format_api_error(e)
    return info
