from pathlib import Path

from alembic import command
from alembic.config import Config
from langgraph.checkpoint.postgres import PostgresSaver

from support_agent.core.config import get_settings
from support_agent.domain.models import Order
from support_agent.repositories.database import create_factory


def main():
    """功能：执行业务迁移、创建检查点表并幂等写入两条合成订单。

    输入：无显式参数；读取应用环境配置，当前目录须包含 alembic.ini。
    输出：None；成功打印初始化提示；修改数据库结构/演示数据，失败上抛异常。
    """
    settings = get_settings()
    command.upgrade(Config(str(Path.cwd() / "alembic.ini")), "head")
    with PostgresSaver.from_conn_string(settings.checkpoint_url) as saver:
        saver.setup()
    factory = create_factory(settings)
    try:
        with factory.begin() as session:
            for order_id, status in (("DEMO-1001", "delayed"), ("DEMO-1002", "delivered")):
                if session.get(Order, order_id) is None:
                    session.add(Order(id=order_id, shipment_status=status))
    finally:
        factory.kw["bind"].dispose()
    print("Business migrations, graph checkpoint tables and synthetic orders initialized")


if __name__ == "__main__":
    main()
