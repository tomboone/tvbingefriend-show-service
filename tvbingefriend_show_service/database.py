"""Database connection for Azure SQL Database using Managed Identity."""

import os
import struct
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

# noinspection PyUnresolvedReferences
from tvbingefriend_show_service.models.base import Base  # noqa: F401

# For local development/testing, a standard connection string can be provided.
# This is useful for SQLite in-memory databases for tests.
SQLALCHEMY_CONNECTION_STRING = os.getenv("SQLALCHEMY_CONNECTION_STRING")

if SQLALCHEMY_CONNECTION_STRING:
    engine = create_engine(SQLALCHEMY_CONNECTION_STRING)
else:
    # In Azure, construct the connection string and connect using Managed Identity.
    from tvbingefriend_show_service import config
    from azure.identity import ManagedIdentityCredential

    credential = ManagedIdentityCredential()

    def get_db_token():
        """Retrieves a new AAD token for the database."""
        # The scope for Azure Database for MySQL
        token = credential.get_token("https://ossrdbms-aad.database.windows.net/.default")
        # For some drivers, the token needs to be passed as a bytes-like object
        return struct.pack("<I", len(token.token)) + token.token.encode("utf-16-le")

    engine = create_engine(
        f"mysql+mysqlconnector://{config.DB_USER}@{config.DB_HOST}/{config.DB_NAME}",
        connect_args={
            "password": get_db_token,
            "auth_plugin": "mysql_clear_password"
        },
        pool_pre_ping=True
    )

    # This event listener is crucial for refreshing the token before each connection.
    @event.listens_for(engine, "do_connect")
    def provide_token(dialect, connrec, cargs, cparams):
        """Provide a new token for each new connection."""
        cparams["password"] = get_db_token()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
