"""Stage one page of shows for upsert"""
import logging

import azure.functions as func

from tvbingefriend_show_service.config import SHOWS_PAGE_QUEUE, STORAGE_CONNECTION_SETTING_NAME
from tvbingefriend_show_service.services.show_service import ShowService

bp: func.Blueprint = func.Blueprint()


@bp.function_name(name="queue_for_upsert")
@bp.queue_trigger(
    arg_name="queuemsg",
    queue_name=SHOWS_PAGE_QUEUE,
    connection=STORAGE_CONNECTION_SETTING_NAME
)
def queue_for_upsert(queuemsg: func.QueueMessage) -> None:
    """Stage one page of shows for upsert

    Args:
        queuemsg (func.QueueMessage): Queue message
    """
    try:
        show_service: ShowService = ShowService()  # create show service
        show_service.queue_shows_for_upsert(queuemsg)  # stage shows for upsert
    except Exception as e:
        logging.error(
            f"stage_shows_for_upsert: Unhandled exception for queue message {queuemsg.id}. Error: {e}",
            exc_info=True
        )
        raise
