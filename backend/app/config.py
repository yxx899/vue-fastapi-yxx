from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_BACKEND_ROOT / ".env", _BACKEND_ROOT / ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = f"sqlite:///{(_BACKEND_ROOT / 'data' / 'knowledge_base.db').as_posix()}"
    secret_key: str = "dev-secret-key-change-in-production"
    access_token_expire_minutes: int = 1440
    algorithm: str = "HS256"

    dashscope_api_key: str = ""
    dashscope_workspace: str = ""
    dashscope_region: str = "cn-beijing"
    # 可选：完整网关根地址，例如 https://ws-xxx.cn-beijing.maas.aliyuncs.com/api/v1
    dashscope_base_url: str = ""
    qwen_model: str = "qwen-plus"
    # 无工作空间时跳过 sk-ws- 密钥；已配置工作空间/专属地址则可使用
    qwen_skip_ws_key: bool = True
    bge_model_name: str = "BAAI/bge-small-zh-v1.5"
    embedding_mock: bool = False

    chroma_persist_dir: str = "./data/chroma"
    upload_dir: str = "./data/uploads"

    chunk_size: int = 800
    chunk_overlap: int = 160
    rag_top_k: int = 6
    # Chroma cosine distance：越小越相似。超过此阈值视为与问题无关，直接拒答。
    rag_max_distance: float = 0.55
    # 多轮对话：带入模型的最近轮数（每轮含用户+助手各一条）
    rag_history_turns: int = 6
    # 跨会话记忆：新建对话时，仍取该用户其他会话最近若干轮作为上下文
    rag_cross_session_turns: int = 4
    rag_cross_session_enabled: bool = True


settings = Settings()
