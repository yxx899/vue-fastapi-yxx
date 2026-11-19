import json
from typing import Any

from fastapi import HTTPException

from app.models.entities import Tenant

# 平台超管可逐项开关的租户能力
DEFAULT_TENANT_FEATURES: dict[str, bool] = {
    "chat": True,
    "knowledge_base": True,
    "document_upload": True,
    "statistics_dashboard": True,
    "user_management": True,
    "department_management": True,
    "audit": True,
    "audit_export": True,
}

FEATURE_LABELS: dict[str, str] = {
    "chat": "AI 问答",
    "knowledge_base": "知识库",
    "document_upload": "文档上传",
    "statistics_dashboard": "统计看板",
    "user_management": "用户管理",
    "department_management": "部门管理",
    "audit": "问答审计",
    "audit_export": "审计 CSV 导出",
}


def parse_tenant_features(raw: str | None) -> dict[str, bool]:
    base = dict(DEFAULT_TENANT_FEATURES)
    if not raw:
        return base
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return base
    if not isinstance(data, dict):
        return base
    for key in DEFAULT_TENANT_FEATURES:
        if key in data:
            base[key] = bool(data[key])
    return base


def serialize_tenant_features(features: dict[str, bool]) -> str:
    merged = parse_tenant_features(None)
    merged.update({k: bool(v) for k, v in features.items() if k in DEFAULT_TENANT_FEATURES})
    return json.dumps(merged, ensure_ascii=False)


def tenant_features(tenant: Tenant) -> dict[str, bool]:
    return parse_tenant_features(getattr(tenant, "features_json", None))


def tenant_policy_payload(tenant: Tenant) -> dict[str, Any]:
    return {
        "is_active": tenant.is_active,
        "expires_at": tenant.expires_at.isoformat() if tenant.expires_at else None,
        "max_knowledge_bases": tenant.max_knowledge_bases,
        "max_documents": tenant.max_documents,
        "max_file_size_mb": tenant.max_file_size_mb,
        "max_users": getattr(tenant, "max_users", 100),
        "features": tenant_features(tenant),
    }


def ensure_tenant_feature(tenant: Tenant, feature: str) -> None:
    feats = tenant_features(tenant)
    if not feats.get(feature, True):
        label = FEATURE_LABELS.get(feature, feature)
        raise HTTPException(
            status_code=403,
            detail=f"平台已关闭本企业的「{label}」功能，请联系平台管理员",
        )
