"""TV Binge Friend Show Service"""
import azure.functions as func

from tvbingefriend_show_service.blueprints import (
    bp_get_details,
    bp_get_index_page,
    bp_queue_for_upsert,
    bp_start_get_all,
    bp_updates_manual,
    bp_updates_timer,
    bp_upsert
)

func_app = func.FunctionApp()

func_app.register_blueprint(bp_get_details)
func_app.register_blueprint(bp_get_index_page)
func_app.register_blueprint(bp_queue_for_upsert)
func_app.register_blueprint(bp_start_get_all)
func_app.register_blueprint(bp_updates_manual)
func_app.register_blueprint(bp_updates_timer)
func_app.register_blueprint(bp_upsert)
