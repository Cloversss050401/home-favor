"""应用配置：从 .env 读取全部环境变量，禁止在业务代码中硬编码密钥。

修复记录（DEF-01 家庭档案无法持久保存）：
- env_file 由相对路径 ".env" 改为基于项目根目录的绝对路径：无论从哪个工作目录
  启动（start.bat / python startup.py / IDE），都能读到同一份 .env，避免回退到
  默认 MySQL 连接串导致"档案读不到/存不上"。
- sqlite 相对路径（sqlite:///./data/ai_recipe.db）统一解析为基于项目根目录的
  绝对路径：无论从哪个目录启动，读写都是同一个数据库文件，杜绝多实例数据漂移
  （表现为"保存后刷新/重启档案丢失"）。
"""

from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根目录 = src/config/settings.py 的上两级
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """全局配置（基于 .env）。"""

    # 服务
    DEBUG: bool = True
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000
    CORS_ORIGINS: list[str] = ["*"]

    # 数据库
    DB_URL: str = "mysql+pymysql://root:password@127.0.0.1:3306/ai_recipe"
    REDIS_URL: str = "redis://127.0.0.1:6379/0"

    # 大模型（AI 食谱生成）
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = ""
    LLM_MODEL: str = ""

    # 多模态 OCR（拍照识别食材）
    MULTIMODAL_API_KEY: str = ""
    MULTIMODAL_BASE_URL: str = ""
    MULTIMODAL_MODEL: str = ""

    # ASR 方言语音（武汉话转文字）
    ASR_API_KEY: str = ""
    ASR_BASE_URL: str = ""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def _resolve_sqlite_absolute(self) -> "Settings":
        """sqlite 相对路径 -> 基于项目根目录的绝对路径（防数据文件漂移）。

        兼容测试注入的绝对路径（sqlite:///C:/...）与 :memory:（sqlite:///:memory:）。
        """
        prefix = "sqlite:///"
        if self.DB_URL.startswith(prefix):
            rel = self.DB_URL[len(prefix) :]
            if rel and rel != ":memory:" and not Path(rel).is_absolute():
                abs_path = (PROJECT_ROOT / rel).resolve()
                self.DB_URL = f"{prefix}{abs_path.as_posix()}"
        return self

    @property
    def llm_ready(self) -> bool:
        """大模型密钥是否就绪。"""
        return bool(self.LLM_API_KEY and self.LLM_BASE_URL)

    @property
    def multimodal_ready(self) -> bool:
        """多模态 OCR 密钥是否就绪。"""
        return bool(self.MULTIMODAL_API_KEY and self.MULTIMODAL_BASE_URL)

    @property
    def asr_ready(self) -> bool:
        """ASR 语音密钥是否就绪。"""
        return bool(self.ASR_API_KEY and self.ASR_BASE_URL)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
