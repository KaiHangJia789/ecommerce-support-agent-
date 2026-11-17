from sqlalchemy.orm import Session

from support_agent.domain.models import OutboxEvent, Run, Ticket


def create_ticket(session: Session, message: str, order_id: str | None) -> dict[str, str]:
    """功能：在调用方事务内创建工单、执行记录和对应 outbox 事件。

    输入：session：已开启事务的 Session；message：问题；order_id：订单号或 None。
    输出：dict[str, str]：ticket_id/run_id；flush 分配 ID，但不自行提交事务。
    """
    ticket = Ticket(message=message, order_id=order_id)
    session.add(ticket)
    session.flush()
    run = Run(ticket_id=ticket.id)
    session.add(run)
    session.flush()
    session.add(OutboxEvent(run_id=run.id))
    return {"ticket_id": ticket.id, "run_id": run.id}
