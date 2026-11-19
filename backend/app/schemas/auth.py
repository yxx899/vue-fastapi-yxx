from pydantic import BaseModel, Field


class TenantLoginIn(BaseModel):
    username: str
    password: str


class PlatformLoginIn(BaseModel):
    username: str
    password: str


class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6, max_length=128)


class TenantPolicyOut(BaseModel):
    is_active: bool
    expires_at: str | None
    max_knowledge_bases: int
    max_documents: int
    max_file_size_mb: int
    max_users: int
    features: dict[str, bool]


class UserOut(BaseModel):
    id: int
    username: str
    display_name: str | None
    role: str
    tenant_id: int
    tenant_name: str
    tenant_policy: TenantPolicyOut | None = None

    model_config = {"from_attributes": True}
