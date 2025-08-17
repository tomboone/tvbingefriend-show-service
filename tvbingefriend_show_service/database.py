"""Database connection for Azure SQL Database (or MySQL as implied by errors)."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tvbingefriend_show_service.config import SQLALCHEMY_CONNECTION_STRING
# noinspection PyUnresolvedReferences
from tvbingefriend_show_service.models.base import Base  # noqa: F401


if not SQLALCHEMY_CONNECTION_STRING:
    raise ValueError("SQLALCHEMY_CONNECTION_STRING is not set in the configuration.")

# Check if the database is SQLite
if SQLALCHEMY_CONNECTION_STRING.startswith("sqlite"):
    # For SQLite, we don't need connection pooling options
    engine = create_engine(SQLALCHEMY_CONNECTION_STRING)
else:
    # For other databases, use the full set of options
    engine = create_engine(
        SQLALCHEMY_CONNECTION_STRING,
        pool_size=5,          # Number of connections to keep open in the pool
        max_overflow=10,      # Number of connections that can be opened beyond pool_size
        pool_recycle=1800,    # Recycle connections after 30 minutes (important for MySQL)
        pool_timeout=30,      # How long to wait for a connection from the pool
        pool_pre_ping=True    # Enable "pre-ping" to test connections before checkout
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
