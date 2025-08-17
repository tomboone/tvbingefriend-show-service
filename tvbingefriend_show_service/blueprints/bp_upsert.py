"""Upsert a show"""
import logging

import azure.functions as func

from tvbingefriend_show_service.config import SHOW_UPSERT_QUEUE, STORAGE_CONNECTION_SETTING_NAME
from tvbingefriend_show_service.utils import db_session_manager
from tvbingefriend_show_service.services.show_service import ShowService

bp: func.Blueprint = func.Blueprint()


@bp.function_name(name="upsert")
@bp.queue_trigger(
    arg_name="upsertmsg",
    queue_name=SHOW_UPSERT_QUEUE,
    connection=STORAGE_CONNECTION_SETTING_NAME,
)
def upsert_show(upsertmsg: func.QueueMessage) -> None:
    """Upsert a show

    Args:
        upsertmsg (func.QueueMessage): Queue message
    """
    try:
        show_service: ShowService = ShowService()  # create show service
        with db_session_manager() as db:
            show_service.upsert_show(upsertmsg, db)  # upsert show
    except Exception as e:  # catch errors and log them
        logging.error(
            f"upsert_show: Unhandled exception for queue message {upsertmsg.id}. Error: {e}",
            exc_info=True
        )
        raise
