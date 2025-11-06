"""Alembic environment configuration"""
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
import sys

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import all models
from src.models.auth import Base as AuthBase
from src.models.trading import Base as TradingBase
from src.models.strategy import Base as StrategyBase
from src.models.market_data import Base as MarketDataBase
from src.models.risk import Base as RiskBase

# Import models for Alembic to track
from src.models import (
    User, Role, Session,
    Order, Trade, Position,
    Strategy, Signal, StrategyPerformance,
    Symbol, OHLCV, MarketData,
    RiskEvent, Drawdown, PortfolioSnapshot
)

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use environment variable for database URL
database_url = os.getenv('DATABASE_URL', 'postgresql://user:pass@localhost/trading')
config.set_main_option('sqlalchemy.url', database_url)

# Combine all model metadata
target_metadata = AuthBase.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

