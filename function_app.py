"""TV Binge Friend Show Service"""
import azure.functions as func

from tvbingefriend_show_service.blueprints import (
    bp_get_details,
    bp_get_index_page,
    bp_start_get_all,
    bp_updates_manual,
    bp_updates_timer,
    bp_health_monitoring,
    bp_get_show_by_id,
    bp_search_shows,
    bp_get_show_summaries,
    bp_get_shows_bulk
)

func_app = func.FunctionApp()

func_app.register_blueprint(bp_get_details)
func_app.register_blueprint(bp_get_index_page)
func_app.register_blueprint(bp_start_get_all)
func_app.register_blueprint(bp_updates_manual)
func_app.register_blueprint(bp_updates_timer)
func_app.register_blueprint(bp_health_monitoring)
func_app.register_blueprint(bp_get_show_by_id)
func_app.register_blueprint(bp_search_shows)
func_app.register_blueprint(bp_get_show_summaries)
func_app.register_blueprint(bp_get_shows_bulk)
