"""Get one show index page"""
import logging

import azure.functions as func

from tvbingefriend_show_service.config import INDEX_QUEUE, STORAGE_CONNECTION_SETTING_NAME
from tvbingefriend_show_service.services.show_service import ShowService

bp: func.Blueprint = func.Blueprint()


@bp.function_name(name="get_index_page")
@bp.queue_trigger(
    arg_name="indexpagemsg",
    queue_name=INDEX_QUEUE,
    connection=STORAGE_CONNECTION_SETTING_NAME
)
def get_index_page(indexpagemsg: func.QueueMessage) -> None:
    """Get one show index page

    Args:
        indexpagemsg (func.QueueMessage): Index page message
    """
    try:
        logging.info("=== PROCESSING INDEX PAGE MESSAGE ===")
        logging.info(f"Message ID: {indexpagemsg.id}")
        logging.info(f"Message content: {indexpagemsg.get_body().decode('utf-8')}")
        logging.info(f"Dequeue count: {indexpagemsg.dequeue_count}")
        logging.info(f"Pop receipt: {indexpagemsg.pop_receipt}")
        
        # Try to parse message content
        try:
            msg_data = indexpagemsg.get_json()
            logging.info(f"Parsed message data: {msg_data}")
        except Exception as parse_e:
            logging.error(f"Failed to parse message JSON: {parse_e}")
            raise
        
        logging.info("Initializing ShowService...")
        show_service: ShowService = ShowService()  # initialize show service
        
        logging.info("Calling show_service.get_shows_index_page...")
        show_service.get_shows_index_page(indexpagemsg)   # get and process show page
        
        logging.info(f"=== SUCCESSFULLY PROCESSED MESSAGE ID: {indexpagemsg.id} ===")
    except Exception as e:  # catch any exceptions, log them, and re-raise them
        logging.error(
            f"=== ERROR PROCESSING MESSAGE ID {indexpagemsg.id} ===",
            exc_info=True
        )
        logging.error(f"Exception type: {type(e).__name__}")
        logging.error(f"Exception message: {str(e)}")
        raise
