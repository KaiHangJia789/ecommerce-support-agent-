import pytest
from pydantic import ValidationError

from support_agent.core.config import Settings


def values(**overrides):
    """功能：生成测试配置并应用指定字段覆盖。

    输入：**overrides：待替换的配置字段；令牌为固定的无效生产假值。
    输出：dict：用于构造 Settings 的合成配置，不读取真实 .env。
    """
    return {
        "database_url": "sqlite://",
        "redis_url": "redis://localhost:6379/0",
        "demo_api_token": "t" * 40,
        **overrides,
    }


def test_missing_token_is_rejected():
    """功能：验证空演示令牌无法通过配置校验。

    输入：无；使用本文件生成的合成配置。
    输出：None；断言抛出 ValidationError。
    """
    with pytest.raises(ValidationError):
        Settings(**values(demo_api_token=""))


def test_secret_is_redacted():
    """功能：验证配置对象的字符串表示不会展示令牌明文。

    输入：无；使用合成 Settings。
    输出：None；断言 repr 不含假令牌。
    """
    settings = Settings(**values())
    assert "t" * 40 not in repr(settings)


def test_production_and_real_provider_fail_closed():
    """功能：验证 P0 拒绝生产运行及真实模型供应商。

    输入：无；分别使用 production 环境和 qwen 供应商的假配置。
    输出：None；断言两种配置均抛出 ValidationError。
    """
    for overrides in ({"app_env": "production"}, {"model_provider": "qwen"}):
        with pytest.raises(ValidationError):
            Settings(**values(**overrides))
