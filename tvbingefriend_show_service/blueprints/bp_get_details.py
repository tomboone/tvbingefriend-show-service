"""Get details about a specific show"""
import logging

import azure.functions as func

from tvbingefriend_show_service.config import DETAILS_QUEUE, STORAGE_CONNECTION_SETTING_NAME
from tvbingefriend_show_service.services.show_service import ShowService

bp: func.Blueprint = func.Blueprint()


@bp.function_name(name="get_details")
@bp.queue_trigger(
    arg_name="detailsmsg",
    queue_name=DETAILS_QUEUE,
    connection=STORAGE_CONNECTION_SETTING_NAME
)
def get_details(detailsmsg: func.QueueMessage):
    """Get show details

    Args:
        detailsmsg (func.QueueMessage): Details message
    """
    try:
        show_service: ShowService = ShowService()  # initialize show service
        show_service.get_show_details(detailsmsg)  # get show details
    except Exception as e:  # catch errors and log them
        logging.error(
            f"get_show_seasons_episodes: Unhandled exception for message ID {detailsmsg.id}. Error: {e}",
            exc_info=True
        )
        raise
