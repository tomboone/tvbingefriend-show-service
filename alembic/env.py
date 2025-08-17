from logging.config import fileConfig
import os
import sys
import json

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Add the project root to the path to allow importing from the service
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
from tvbingefriend_show_service.models.base import Base
from tvbingefriend_show_service.models.show import Show  # noqa: F401
target_metadata = Base.metadata

def get_connection_string():
    """Gets the connection string from config.py or local.settings.json."""
    try:
        # First, try to get the connection string from the config module.
        # This is expected to be populated from an environment variable.
        from tvbingefriend_show_service.config import SQLALCHEMY_CONNECTION_STRING
        if SQLALCHEMY_CONNECTION_STRING:
            return SQLALCHEMY_CONNECTION_STRING
    except (ImportError, ValueError):
        pass

    # If the environment variable is not set, fall back to local.settings.json.
    # Since this file is in .aiexclude, I am assuming its structure.
    # You may need to edit this if your file is different.
    try:
        settings_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'local.settings.json'))
        with open(settings_path) as f:
            settings = json.load(f)
        return settings['Values']['SQLALCHEMY_CONNECTION_STRING']
    except (FileNotFoundError, KeyError):
        raise RuntimeError("Database connection string not found in config.py or local.settings.json")

# Set the sqlalchemy.url from our dynamic source
config.set_main_option('sqlalchemy.url', get_connection_string())


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
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
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
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
