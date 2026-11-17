from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", hide_input_in_errors=True)

    app_env: Literal["development", "test"] = "development"
    model_provider: Literal["mock"] = "mock"
    database_url: SecretStr
    redis_url: SecretStr
    demo_api_token: SecretStr

    @field_validator("demo_api_token")
    @classmethod
    def require_token(cls, value: SecretStr) -> SecretStr:
        """功能：拒绝过短或明显为占位符的演示令牌。

        输入：cls：配置类；value：SecretStr 包装的候选令牌。
        输出：SecretStr：原令牌；校验失败抛出不包含令牌值的 ValueError。
        """
        token = value.get_secret_value()
        if len(token) < 32 or token.lower().startswith(("change", "example", "replace")):
            raise ValueError("DEMO_API_TOKEN requires at least 32 characters")
        return value

    @property
    def sqlalchemy_url(self) -> str:
        """功能：提取 SQLAlchemy 使用的数据库连接串。

        输入：self：包含 database_url 密文包装值的配置实例。
        输出：str：明文连接串，仅供内部驱动使用，不能记录到日志。
        """
        return self.database_url.get_secret_value()

    @property
    def checkpoint_url(self) -> str:
        """功能：将 SQLAlchemy 连接串转换为 psycopg 检查点连接串。

        输入：self：配置实例，隐式读取 sqlalchemy_url。
        输出：str：使用 postgresql:// 前缀的明文连接串，仅供内部使用。
        """
        return self.sqlalchemy_url.replace("postgresql+psycopg://", "postgresql://", 1)


@lru_cache
def get_settings() -> Settings:
    """功能：从进程环境读取、校验并缓存应用配置。

    输入：无显式参数；隐式读取环境变量，配置必须满足 Settings 约束。
    输出：Settings：缓存的配置实例；缺失或无效配置抛出校验异常。
    """
    return Settings()
