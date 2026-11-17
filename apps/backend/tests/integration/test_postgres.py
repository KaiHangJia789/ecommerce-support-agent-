import os
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from langgraph.checkpoint.postgres import PostgresSaver
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from support_agent.agents.workflow import build_graph
from support_agent.domain.models import OutboxEvent, Run, utc_now
from support_agent.services.tickets import create_ticket
from support_agent.tasks.execution import dispatch_pending, execute_run

pytestmark = pytest.mark.integration


@pytest.fixture
def pg_factory():
    """功能：为集成测试提供真实 PostgreSQL 会话工厂。

    输入：隐式读取 TEST_DATABASE_URL；未配置时跳过测试。
    输出：yield sessionmaker；测试结束释放连接池，不删除数据库。
    """
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is not configured")
    engine = create_engine(url, pool_pre_ping=True)
    factory = sessionmaker(engine, expire_on_commit=False)
    yield factory
    engine.dispose()


def test_concurrent_delivery_and_checkpoint_survive_new_connection(pg_factory):
    """功能：验证并发重复消费只执行一次，且新连接仍可读取持久化检查点。

    输入：pg_factory：独立测试数据库的会话工厂。
    输出：None；断言成功、一次尝试及重新连接后的回复一致。
    """
    with pg_factory.begin() as session:
        ids = create_ticket(session, "物流一直没更新", "DEMO-1001")

    def consume(_):
        """功能：在独立检查点连接中消费同一执行，模拟并发投递。

        输入：_：线程池序号，不参与业务；闭包读取工单 ID 和 pg_factory。
        输出：None；执行工作流并自动关闭检查点连接。
        """
        url = pg_factory.kw["bind"].url.render_as_string(hide_password=False)
        with PostgresSaver.from_conn_string(
            url.replace("postgresql+psycopg", "postgresql")
        ) as saver:
            execute_run(ids["run_id"], pg_factory, saver)

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(consume, range(2)))
    with pg_factory() as session:
        run = session.get(Run, ids["run_id"])
        assert run.status == "succeeded"
        assert run.attempts == 1
        thread_id = run.thread_id
        reply = run.result["reply"]
    url = pg_factory.kw["bind"].url.render_as_string(hide_password=False)
    with PostgresSaver.from_conn_string(url.replace("postgresql+psycopg", "postgresql")) as saver:
        state = build_graph(saver).get_state({"configurable": {"thread_id": thread_id}})
        assert state.values["reply"] == reply


def test_abandoned_delivery_is_published_again(pg_factory):
    """功能：验证超出重投窗口的未完成事件可再次发布。

    输入：pg_factory：独立测试数据库会话工厂。
    输出：None；断言发送列表包含被标记为过期的执行 ID。
    """
    with pg_factory.begin() as session:
        ids = create_ticket(session, "查询物流", "DEMO-1002")
        session.flush()
        event = session.scalar(select(OutboxEvent).where(OutboxEvent.run_id == ids["run_id"]))
        event.last_sent_at = utc_now() - timedelta(seconds=31)
    sent = []
    dispatch_pending(pg_factory, sent.append)
    assert ids["run_id"] in sent
