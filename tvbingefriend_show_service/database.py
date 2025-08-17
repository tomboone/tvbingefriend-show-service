"""Database connection for Azure SQL Database using Managed Identity."""

import os
import struct
from azure.identity import ManagedIdentityCredential
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

# noinspection PyUnresolvedReferences
from tvbingefriend_show_service.models.base import Base  # noqa: F401

# Configuration for Managed Identity
db_host = os.environ.get("DB_HOST")
db_name = os.environ.get("DB_NAME")
db_user = os.environ.get("DB_USER")

if not all([db_host, db_name, db_user]):
    raise ValueError("DB_HOST, DB_NAME, and DB_USER environment variables must be set.")

# For local development, you might use a standard connection string
# For Azure, we use Managed Identity
connection_string = os.environ.get("SQLALCHEMY_CONNECTION_STRING")

if connection_string:
    engine = create_engine(connection_string)
else:
    # In Azure, connect using Managed Identity
    credential = ManagedIdentityCredential()

    def get_db_token():
        # The scope for Azure Database for MySQL
        token = credential.get_token("https://ossrdbms-aad.database.windows.net/.default")
        # For some drivers, the token needs to be passed as a bytes-like object
        return struct.pack("<I", len(token.token)) + token.token.encode("utf-16-le")

    engine = create_engine(
        f"mysql+mysqlconnector://{db_user}@{db_host}/{db_name}",
        connect_args={
            "password": get_db_token,
            "auth_plugin": "mysql_clear_password"
        },
        pool_pre_ping=True
    )

    # This event listener is crucial for refreshing the token
    @event.listens_for(engine, "do_connect")
    def provide_token(dialect, connrec, cargs, cparams):
        # Overwrite the password with a new token
        cparams["password"] = get_db_token()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
