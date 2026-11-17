"""Initial business tables. Graph checkpoint tables are managed by PostgresSaver.setup."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """功能：启用 pgvector 并建立订单、工单、执行和 outbox 表及索引。

    输入：无显式参数；使用 Alembic 当前数据库迁移上下文。
    输出：None；修改数据库结构，图检查点表由 PostgresSaver 单独管理。
    """
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "orders",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("shipment_status", sa.String(32), nullable=False),
    )
    op.create_table(
        "tickets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("order_id", sa.String(64)),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("ticket_id", sa.String(36), sa.ForeignKey("tickets.id"), nullable=False),
        sa.Column("thread_id", sa.String(36), nullable=False, unique=True),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("graph_version", sa.String(32), nullable=False),
        sa.Column("result", sa.JSON()),
        sa.Column("error_code", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_agent_runs_ticket_id", "agent_runs", ["ticket_id"])
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "run_id", sa.String(36), sa.ForeignKey("agent_runs.id"), nullable=False, unique=True
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_sent_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_outbox_pending", "outbox_events", ["completed_at", "last_sent_at"])


def downgrade():
    """功能：按依赖顺序删除本次迁移创建的业务表。

    输入：无显式参数；使用 Alembic 当前数据库迁移上下文。
    输出：None；删除四张业务表及其数据，不移除 vector 扩展或图检查点表。
    """
    for name in ("outbox_events", "agent_runs", "tickets", "orders"):
        op.drop_table(name)
