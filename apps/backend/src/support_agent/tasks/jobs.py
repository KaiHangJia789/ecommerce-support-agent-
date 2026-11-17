import logging

from langgraph.checkpoint.postgres import PostgresSaver

from support_agent.repositories.database import create_factory
from support_agent.tasks.app import app, settings
from support_agent.tasks.execution import dispatch_pending, execute_run, record_failure

logger = logging.getLogger("support_agent")


@app.task(name="support.dispatch")
def dispatch():
    """功能：由 Beat 调用，将待处理 outbox 事件投递到 Celery。

    输入：无显式参数；隐式使用任务应用、配置与数据库会话工厂。
    输出：int：本批成功投递数；结束时释放自建连接池。
    """
    factory = create_factory(settings)
    try:
        # 功能：发布执行任务；输入：run_id；输出：Celery AsyncResult，不等待结果。
        return dispatch_pending(
            factory, lambda run_id: app.send_task("support.execute", args=[run_id], retry=False)
        )
    finally:
        factory.kw["bind"].dispose()


@app.task(name="support.execute")
def execute(run_id: str):
    """功能：为单次执行创建检查点连接，执行工作流并记录失败。

    输入：run_id：Celery 消息携带的执行 ID；隐式使用当前应用配置。
    输出：None；业务结果写入数据库，异常只记录类型并计入失败；最后释放连接池。
    """
    factory = create_factory(settings)
    try:
        with PostgresSaver.from_conn_string(settings.checkpoint_url) as saver:
            execute_run(run_id, factory, saver)
    except Exception as error:
        logger.error(
            "workflow_failed", extra={"run_id": run_id, "error_type": type(error).__name__}
        )
        record_failure(run_id, factory)
    finally:
        factory.kw["bind"].dispose()
