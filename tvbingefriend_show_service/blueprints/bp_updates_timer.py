"""Update shows from TV Maze"""
import logging

import azure.functions as func

from tvbingefriend_show_service.config import UPDATES_NCRON
from tvbingefriend_show_service.services.show_service import ShowService

bp: func.Blueprint = func.Blueprint()


# noinspection PyUnusedLocal
@bp.function_name(name="get_updates_timer")
@bp.timer_trigger(
    arg_name="updateshows",
    schedule=UPDATES_NCRON,
    run_on_startup=False
)
def get_updates_timer(updateshows: func.TimerRequest) -> None:
    """Update shows from TV Maze"""
    try:
        show_service: ShowService = ShowService()  # create show service
        show_service.get_updates()  # get updates
    except Exception as e:   # catch errors and log them
        logging.error(
            f"get_updates_timer: Unhandled exception. Error: {e}",
            exc_info=True
        )
        raise
