import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from support_agent.domain.models import Base, Order


@pytest.fixture
def factory():
    """功能：提供隔离的内存数据库及一条合成订单供单元测试使用。

    输入：无；pytest 自动管理夹具生命周期。
    输出：yield sessionmaker；清理阶段释放 SQLite 连接池。
    """
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory.begin() as session:
        session.add(Order(id="DEMO-1001", shipment_status="delayed"))
    yield factory
    engine.dispose()
