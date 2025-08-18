"""Blueprints for the show service"""
from tvbingefriend_show_service.blueprints.bp_get_details import bp as bp_get_details
from tvbingefriend_show_service.blueprints.bp_get_index_page import bp as bp_get_index_page
from tvbingefriend_show_service.blueprints.bp_start_get_all import bp as bp_start_get_all
from tvbingefriend_show_service.blueprints.bp_updates_manual import bp as bp_updates_manual
from tvbingefriend_show_service.blueprints.bp_updates_timer import bp as bp_updates_timer

__all__ = [
    "bp_get_details",
    "bp_get_index_page",
    "bp_start_get_all",
    "bp_updates_manual",
    "bp_updates_timer",
]
