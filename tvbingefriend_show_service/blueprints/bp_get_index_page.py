"""Get one show index page"""
import logging

import azure.functions as func

from tvbingefriend_show_service.config import SHOWS_INDEX_QUEUE, STORAGE_CONNECTION_SETTING_NAME
from tvbingefriend_show_service.services.show_service import ShowService

bp: func.Blueprint = func.Blueprint()


@bp.function_name(name="get_index_page")
@bp.queue_trigger(
    arg_name="indexpagemsg",
    queue_name=SHOWS_INDEX_QUEUE,
    connection=STORAGE_CONNECTION_SETTING_NAME
)
def get_index_page(indexpagemsg: func.QueueMessage) -> None:
    """Get one show index page

    Args:
        indexpagemsg (func.QueueMessage): Index page message
    """
    try:
        show_service: ShowService = ShowService()  # initialize show service
        show_service.get_shows_index_page(indexpagemsg)   # get and process show page
    except Exception as e:  # catch any exceptions, log them, and re-raise them
        logging.error(
            f"get_show_page: Unhandled exception for message ID {indexpagemsg.id}. Error: {e}",
            exc_info=True
        )
        raise
