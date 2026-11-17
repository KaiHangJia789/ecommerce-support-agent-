from langgraph.checkpoint.memory import InMemorySaver
from sqlalchemy import select

from support_agent.agents.workflow import build_graph
from support_agent.domain.models import OutboxEvent, Run, Ticket
from support_agent.services.tickets import create_ticket
from support_agent.tasks.execution import dispatch_pending, execute_run, record_failure


def test_workflow_is_explicit_mock_and_persists_checkpoint():
    """功能：验证工作流显式使用 Mock 并保存可读取的图检查点。

    输入：无；内部使用 InMemorySaver 与合成物流问题。
    输出：None；断言意图、模式、模拟回复及检查点内容。
    """
    graph = build_graph(InMemorySaver())
    config = {"configurable": {"thread_id": "test-run"}}
    result = graph.invoke(
        {"message": "物流没更新", "order_id": "DEMO-1001", "shipment_status": "delayed"}, config
    )
    assert result["intent"] == "logistics"
    assert result["mode"] == "mock"
    assert "模拟" in result["reply"]
    assert graph.get_state(config).values["reply"] == result["reply"]


def test_duplicate_execution_does_not_duplicate_result(factory):
    """功能：验证同一任务重复消费不会重复执行业务效果。

    输入：factory：内存数据库会话工厂。
    输出：None；断言成功状态、尝试数为一、工单状态及事件完成时间。
    """
    with factory.begin() as session:
        ids = create_ticket(session, "物流没更新", "DEMO-1001")
    saver = InMemorySaver()
    execute_run(ids["run_id"], factory, saver)
    execute_run(ids["run_id"], factory, saver)
    with factory() as session:
        run = session.get(Run, ids["run_id"])
        assert run.status == "succeeded"
        assert run.attempts == 1
        assert run.result["mode"] == "mock"
        assert session.get(Ticket, ids["ticket_id"]).status == "resolved"
        assert session.scalar(select(OutboxEvent)).completed_at is not None


def test_missing_order_waits_for_customer(factory):
    """功能：验证未找到合成订单时进入等待客户补充状态。

    输入：factory：内存数据库会话工厂。
    输出：None；断言工单状态为 waiting_customer。
    """
    with factory.begin() as session:
        ids = create_ticket(session, "查询物流", "UNKNOWN")
    execute_run(ids["run_id"], factory, InMemorySaver())
    with factory() as session:
        assert session.get(Ticket, ids["ticket_id"]).status == "waiting_customer"


def test_recovered_execution_clears_failure(factory):
    """功能：验证失败后成功恢复会清除旧错误代码。

    输入：factory：内存数据库会话工厂。
    输出：None；断言 succeeded、error_code=None、尝试数为二。
    """
    with factory.begin() as session:
        ids = create_ticket(session, "查询物流", "DEMO-1001")
    record_failure(ids["run_id"], factory)
    execute_run(ids["run_id"], factory, InMemorySaver())
    with factory() as session:
        run = session.get(Run, ids["run_id"])
        assert run.status == "succeeded"
        assert run.error_code is None
        assert run.attempts == 2


def test_failed_publish_preserves_outbox_for_later(factory):
    """功能：验证队列发布故障保留事件，恢复后可投递且不立即重复投递。

    输入：factory：内存数据库会话工厂。
    输出：None；断言投递数、执行 ID 与事件仍等待完成。
    """
    with factory.begin() as session:
        ids = create_ticket(session, "物流没更新", "DEMO-1001")

    def unavailable(_):
        """功能：模拟消息队列不可连接的发布函数。

        输入：_：待发布的 run_id，此故障桩不使用该参数。
        输出：不正常返回；始终抛出 ConnectionError。
        """
        raise ConnectionError("broker unavailable")

    assert dispatch_pending(factory, unavailable) == 0
    sent = []
    assert dispatch_pending(factory, sent.append) == 1
    assert sent == [ids["run_id"]]
    assert dispatch_pending(factory, sent.append) == 0
    with factory() as session:
        assert session.scalar(select(OutboxEvent)).completed_at is None
