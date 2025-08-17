"""Database connection for Azure SQL Database using Managed Identity."""

import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

# noinspection PyUnresolvedReferences
from tvbingefriend_show_service.models.base import Base  # noqa: F401
from tvbingefriend_show_service import config

# For local development/testing, a standard connection string can be provided.
# This is useful for SQLite in-memory databases for tests.
SQLALCHEMY_CONNECTION_STRING = os.getenv("SQLALCHEMY_CONNECTION_STRING")

if SQLALCHEMY_CONNECTION_STRING:
    # Use a direct connection string, mainly for tests with SQLite.
    engine = create_engine(SQLALCHEMY_CONNECTION_STRING)
elif config.DB_PASSWORD:
    # For local development, connect using a password.
    engine = create_engine(
        f"mysql+pymysql://{config.DB_USER}:{config.DB_PASSWORD}@{config.DB_HOST}/{config.DB_NAME}"
    )
else:
    # In Azure, construct the connection string and connect using Managed Identity.
    from azure.identity import ManagedIdentityCredential

    credential = ManagedIdentityCredential()

    def get_db_token() -> str:
        """Retrieves a new AAD token for the database."""
        # The scope for Azure Database for MySQL
        token = credential.get_token("https://ossrdbms-aad.database.windows.net/.default")
        return token.token

    engine = create_engine(
        f"mysql+pymysql://{config.DB_USER}@{config.DB_HOST}/{config.DB_NAME}",
        connect_args={
            "password": get_db_token,
        },
        pool_pre_ping=True
    )

    # This event listener is crucial for refreshing the token before each connection.
    @event.listens_for(engine, "do_connect")
    def provide_token(dialect, connrec, cargs, cparams):
        """Provide a new token for each new connection."""
        cparams["password"] = get_db_token()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
