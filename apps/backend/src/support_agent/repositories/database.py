from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from support_agent.core.config import Settings


def create_factory(settings: Settings):
    """功能：创建带连接存活检测的 SQLAlchemy 会话工厂。

    输入：settings：含数据库连接配置的 Settings。
    输出：sessionmaker：提交后对象不失效；调用方负责事务与连接池释放。
    """
    return sessionmaker(
        create_engine(settings.sqlalchemy_url, pool_pre_ping=True), expire_on_commit=False
    )
