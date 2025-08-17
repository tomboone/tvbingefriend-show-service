"""Configurations for the show service"""
import os


def _get_required_env(var_name: str) -> str:
    """Gets a required environment variable or raises a ValueError."""
    value = os.getenv(var_name)
    if value is None:
        raise ValueError(f"Missing required environment variable: '{var_name}'")
    return value


STORAGE_CONNECTION_SETTING_NAME: str = "AzureWebJobsStorage"
STORAGE_CONNECTION_STRING: str | None = os.getenv(STORAGE_CONNECTION_SETTING_NAME)

DB_HOST: str = _get_required_env("DB_HOST")
DB_NAME: str = _get_required_env("DB_NAME")
DB_USER: str = _get_required_env("DB_USER")

SHOWS_INDEX_QUEUE: str = os.getenv("SHOWS_INDEX_QUEUE", "index-queue")

SHOWS_PAGE_QUEUE: str = os.getenv("SHOWS_PAGE_QUEUE", "shows-page-queue")
SHOWS_PAGE_CONTAINER: str = os.getenv("SHOWS_PAGE_CONTAINER", "shows-page-container")

SHOW_UPSERT_QUEUE: str = os.getenv("SHOW_UPSERT_QUEUE", "shows-upsert-queue")
SHOW_UPSERT_CONTAINER: str = os.getenv("SHOW_UPSERT_CONTAINER", "shows-upsert-container")

SHOW_DETAILS_QUEUE: str = os.getenv("SHOW_DETAILS_QUEUE", "shows-details-queue")

SHOW_IDS_TABLE: str = os.getenv("SHOW_IDS_TABLE", "shows-ids-table")

UPDATES_NCRON: str = os.getenv("UPDATES_NCRON", "0 0 2 * * *")
