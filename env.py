from logging.config import fileConfig
import os
import json

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# By importing the models package, we ensure that all models
# that are imported into models/__init__.py are registered with
# the Base.metadata object.
from alma_item_checks_webhook_service import models
target_metadata = models.Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_connection_string()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def get_connection_string():
    """Gets the connection string from env or local.settings.json."""
    connection_string = os.getenv("SQLALCHEMY_CONNECTION_STRING")
    if connection_string:
        return connection_string

    local_settings_path = os.path.join(
        os.path.dirname(__file__), "..", "local.settings.json"
    )
    if os.path.exists(local_settings_path):
        with open(local_settings_path) as f:
            local_settings = json.load(f)
        try:
            return local_settings["Values"]["SQLALCHEMY_CONNECTION_STRING"]
        except KeyError:
            raise KeyError(
                "SQLALCHEMY_CONNECTION_STRING not found in local.settings.json"
            )
    raise ValueError("Database connection string not found.")


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Get connection string from env var or local.settings.json
    db_url = get_connection_string()

    # The `config` object is not directly connected to the Engine, so we need to update the `sqlalchemy.url` in the config.
    config.set_main_option("sqlalchemy.url", db_url)

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
