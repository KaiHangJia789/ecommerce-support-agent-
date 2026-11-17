from alembic import context
from sqlalchemy import create_engine

from support_agent.core.config import get_settings
from support_agent.domain.models import Base

engine = create_engine(get_settings().sqlalchemy_url)
try:
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()
finally:
    engine.dispose()
