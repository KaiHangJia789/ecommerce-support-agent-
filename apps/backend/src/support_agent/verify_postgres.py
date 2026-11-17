"""Run integration tests in a separate, non-destructively initialized local database."""

import os
import subprocess
import sys

import psycopg

from support_agent.core.config import get_settings
from support_agent.repositories.database import create_factory


def main():
    """功能：初始化独立 support_test 数据库并运行真实 PostgreSQL 集成测试。

    输入：无显式参数；development/test 环境配置，当前目录为后端目录。
    输出：None；子进程输出初始化/测试结果，失败抛出异常；不删除已有业务或测试数据库。
    """
    settings = get_settings()
    if settings.app_env not in ("development", "test"):
        raise SystemExit("Integration verification is local-only")
    with psycopg.connect(settings.checkpoint_url, autocommit=True) as connection:
        if (
            connection.execute(
                "SELECT 1 FROM pg_database WHERE datname = 'support_test'"
            ).fetchone()
            is None
        ):
            connection.execute("CREATE DATABASE support_test")
    factory = create_factory(settings)
    try:
        test_url = (
            factory.kw["bind"]
            .url.set(database="support_test")
            .render_as_string(hide_password=False)
        )
    finally:
        factory.kw["bind"].dispose()
    env = {**os.environ, "DATABASE_URL": test_url, "TEST_DATABASE_URL": test_url}
    subprocess.run([sys.executable, "-m", "support_agent.initialize"], env=env, check=True)
    subprocess.run([sys.executable, "-m", "pytest", "tests/integration", "-q"], env=env, check=True)


if __name__ == "__main__":
    main()
