import logging
from datetime import timedelta

from sqlalchemy import or_, select

from support_agent.agents.workflow import build_graph
from support_agent.domain.models import Order, OutboxEvent, Run, Ticket, utc_now

logger = logging.getLogger("support_agent")


def dispatch_pending(factory, publish) -> int:
    """功能：锁定最多 50 条可投递事件，发布任务并更新最近发送时间。

    输入：factory：会话工厂；publish：接收 run_id 的投递函数。
    输出：int：成功投递数；首次发布失败则停止本批，未完成事件 30 秒后可重投。
    """
    count = 0
    with factory.begin() as session:
        events = session.scalars(
            select(OutboxEvent)
            .where(
                OutboxEvent.completed_at.is_(None),
                or_(
                    OutboxEvent.last_sent_at.is_(None),
                    OutboxEvent.last_sent_at < utc_now() - timedelta(seconds=30),
                ),
            )
            .order_by(OutboxEvent.created_at)
            .limit(50)
            .with_for_update(skip_locked=True)
        ).all()
        for event in events:
            try:
                publish(event.run_id)
            except Exception as error:
                logger.warning(
                    "outbox_publish_failed",
                    extra={"run_id": event.run_id, "error_type": type(error).__name__},
                )
                break
            event.last_sent_at = utc_now()
            count += 1
    return count


def execute_run(run_id: str, factory, checkpointer) -> None:
    """功能：持有执行记录行锁完成 Mock 图，并在事务内保存结果和事件终态。

    输入：run_id：执行 ID；factory：会话工厂；checkpointer：图检查点存储。
    输出：None；缺失/终态执行直接返回；成功更新结果、工单和 outbox，异常回滚后上抛。
    """
    # Hold the PostgreSQL row lock throughout the graph: retries cannot run concurrently.
    with factory.begin() as session:
        run = session.scalar(select(Run).where(Run.id == run_id).with_for_update())
        if run is None or run.status in ("succeeded", "failed"):
            return
        if run.graph_version != "p0-mock-v1":
            raise ValueError("unsupported graph version")
        ticket = session.get(Ticket, run.ticket_id)
        order = session.get(Order, ticket.order_id) if ticket.order_id else None
        run.status = "running"
        run.attempts += 1
        graph = build_graph(checkpointer)
        config = {"configurable": {"thread_id": run.thread_id}}
        result = graph.invoke(
            {
                "message": ticket.message,
                "order_id": ticket.order_id,
                "shipment_status": order.shipment_status if order else None,
            },
            config,
        )
        run.result = result
        run.status = "succeeded"
        run.error_code = None
        run.finished_at = utc_now()
        ticket.status = result["ticket_status"]
        event = session.scalar(select(OutboxEvent).where(OutboxEvent.run_id == run_id))
        event.completed_at = utc_now()
        logger.info("run_completed", extra={"run_id": run.id, "status": run.status})


def record_failure(run_id: str, factory) -> None:
    """功能：记录失败尝试，达到三次失败时结束执行和 outbox 事件。

    输入：run_id：执行 ID；factory：会话工厂。
    输出：None；更新尝试数/安全错误码；缺失或已经终态的执行不修改。
    """
    with factory.begin() as session:
        run = session.scalar(select(Run).where(Run.id == run_id).with_for_update())
        if run is None or run.status in ("succeeded", "failed"):
            return
        run.attempts += 1
        run.error_code = "workflow_failed"
        if run.attempts >= 3:
            run.status = "failed"
            run.finished_at = utc_now()
            event = session.scalar(select(OutboxEvent).where(OutboxEvent.run_id == run_id))
            event.completed_at = utc_now()
