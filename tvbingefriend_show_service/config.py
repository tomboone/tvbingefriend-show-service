"""Configurations for the show service"""
import os
import json
from typing import Any


def _load_local_settings() -> dict[str, Any]:
    """Loads settings from local.settings.json if it exists."""
    try:
        # The config file is in tvbingefriend_show_service/, so go up one level for project root
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        settings_path = os.path.join(project_root, 'local.settings.json')
        with open(settings_path) as f:
            return json.load(f).get("Values", {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


_local_settings = _load_local_settings()


def _get_setting(var_name: str, required: bool = True, default: Any = None) -> str | None:
    """
    Gets a setting from environment variables or local.settings.json.
    Priority:
    1. Environment variables
    2. local.settings.json
    """
    value = os.getenv(var_name) or _local_settings.get(var_name)
    if value is None:
        if required:
            raise ValueError(f"Missing required setting: '{var_name}'")
        return default
    return value


STORAGE_CONNECTION_SETTING_NAME: str = "AzureWebJobsStorage"
STORAGE_CONNECTION_STRING: str | None = _get_setting(STORAGE_CONNECTION_SETTING_NAME, required=False)

DB_HOST: str | None = _get_setting("DB_HOST")
DB_NAME: str | None = _get_setting("DB_NAME")
DB_USER: str | None = _get_setting("DB_USER")
DB_PASSWORD: str | None = _get_setting("DB_PASSWORD", required=False)

SHOWS_INDEX_QUEUE: str | None = _get_setting("SHOWS_INDEX_QUEUE", required=False, default="index-queue")

SHOWS_PAGE_QUEUE: str | None = _get_setting("SHOWS_PAGE_QUEUE", required=False, default="page-queue")
SHOWS_PAGE_CONTAINER: str | None = _get_setting("SHOWS_PAGE_CONTAINER", required=False, default="page-container")

SHOW_UPSERT_QUEUE: str | None = _get_setting("SHOW_UPSERT_QUEUE", required=False, default="upsert-queue")
SHOW_UPSERT_CONTAINER: str | None = _get_setting(
    "SHOW_UPSERT_CONTAINER", required=False, default="upsert-container"
)

SHOW_DETAILS_QUEUE: str | None = _get_setting("SHOW_DETAILS_QUEUE", required=False, default="details-queue")

SHOW_IDS_TABLE: str | None = _get_setting("SHOW_IDS_TABLE", required=False, default="ids-table")

UPDATES_NCRON: str | None = _get_setting("UPDATES_NCRON", required=False, default="0 0 2 * * *")
