"""Blueprints for the show service"""
from tvbingefriend_show_service.blueprints.bp_get_details import bp as bp_get_details
from tvbingefriend_show_service.blueprints.bp_get_index_page import bp as bp_get_index_page
from tvbingefriend_show_service.blueprints.bp_start_get_all import bp as bp_start_get_all
from tvbingefriend_show_service.blueprints.bp_updates_manual import bp as bp_updates_manual
from tvbingefriend_show_service.blueprints.bp_updates_timer import bp as bp_updates_timer
from tvbingefriend_show_service.blueprints.bp_health_monitoring import bp as bp_health_monitoring
from tvbingefriend_show_service.blueprints.bp_get_show_by_id import bp as bp_get_show_by_id
from tvbingefriend_show_service.blueprints.bp_search_shows import bp as bp_search_shows
from tvbingefriend_show_service.blueprints.bp_get_show_summaries import bp as bp_get_show_summaries
from tvbingefriend_show_service.blueprints.bp_get_shows_bulk import bp as bp_get_shows_bulk

__all__ = [
    "bp_get_details",
    "bp_get_index_page",
    "bp_start_get_all",
    "bp_updates_manual",
    "bp_updates_timer",
    "bp_health_monitoring",
    "bp_get_show_by_id",
    "bp_search_shows",
    "bp_get_show_summaries",
    "bp_get_shows_bulk"
]
