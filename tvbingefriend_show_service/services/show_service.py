"""Service for TV show-related operations."""
import logging
from typing import Any

import azure.functions as func
from tvbingefriend_azure_storage_service import StorageService  # type: ignore
from tvbingefriend_tvmaze_client.tvmaze_api import TVMazeAPI  # type: ignore

from tvbingefriend_show_service.config import (
    STORAGE_CONNECTION_STRING,
    DETAILS_QUEUE,
    SHOW_IDS_TABLE,
    INDEX_QUEUE
)
from tvbingefriend_show_service.repos.show_repo import ShowRepository
from tvbingefriend_show_service.utils import db_session_manager


# noinspection PyMethodMayBeStatic
class ShowService:
    """Service for TV show-related operations."""
    def __init__(self, show_repository: ShowRepository | None = None) -> None:
        self.show_repository = show_repository or ShowRepository()
        self.storage_service = StorageService(STORAGE_CONNECTION_STRING)
        self.tvmaze_api = TVMazeAPI()

    def start_get_all_shows(self, page: int = 0) -> None:
        """Start get all shows from TV Maze

        Args:
            page (int): Page number to start from. Defaults to 0.
        """
        logging.info(f"ShowService.start_get_shows: Starting show retrieval from page {page}")

        start_message: dict[str, Any] = {  # create message to retrieve first page of shows
            "page": page  # page number
        }

        self.storage_service.upload_queue_message(  # upload message to queue
            queue_name=INDEX_QUEUE,  # queue name
            message=start_message  # message to upload
        )

        logging.info(f"ShowService.start_get_shows: Queued page {page} for retrieval")

    def get_shows_index_page(self, indexmsg: func.QueueMessage) -> None:
        """Get one page of shows from TV Maze

        Args:
            indexmsg (func.QueueMessage): Page index message
        """
        page_number: int | None = indexmsg.get_json().get("page")  # get page number from message

        if page_number is None:  # if page number is missing, log error and return
            logging.error("Queue message is missing 'page' number.")
            return

        logging.info(f"ShowService.get_show_page: Getting shows from TV Maze for page_number: {page_number}")

        shows: list[dict[str, Any]] | None = self.tvmaze_api.get_shows(page_number)  # get one page from show index

        if shows:  # if shows are returned, upload data and queue claim ticket
            for show in shows:  # for each show
                if not show or not isinstance(show, dict):
                    logging.error("ShowService.upsert_show: Show not found.")
                    continue
                with db_session_manager() as db:
                    self.show_repository.upsert_show(show, db)  # upsert show

    def get_show_details(self, show_id_msg: func.QueueMessage) -> None:
        """Get show details

        Args:
            show_id_msg (func.QueueMessage): Show ID message
        """
        show_id: int | None = show_id_msg.get_json().get("show_id")
        if show_id is None:
            logging.error("Queue message is missing 'show_id' number.")
            return

        show: dict[str, Any] = self.tvmaze_api.get_show_details(show_id)
        if not show:
            logging.error(f"ShowService.get_show_details: Failed to get show ID {show_id}")
            return

        with db_session_manager() as db:
            self.show_repository.upsert_show(show, db)

    def get_updates(self, since: str = "day"):
        """Get updates

        Args:
            since (str): Since parameter for TV Maze API. Defaults to "day".
        """
        logging.info("ShowService.get_updates: Get updates")
        tvmaze_api: TVMazeAPI = TVMazeAPI()  # initialize TV Maze API client
        updates: dict[str, Any] = tvmaze_api.get_show_updates(period=since)  # get show updates

        for show_id, last_updated in updates.items():  # for each show update
            details_queue_msg = {
                "show_id": int(show_id),
            }
            self.queue_show_details(details_queue_msg)  # queue show for details retrieval
            self.update_id_table(int(show_id), int(last_updated))  # update show ID table

    def get_shows_page_number(self, req: func.HttpRequest) -> int | func.HttpResponse:
        """Validate show page number
        Args:
            req (func.HttpRequest): Request object
        Returns:
            int | func.HttpResponse: Page number or error response
        """
        page: int = 0  # default page number
        page_str: str | None = req.params.get('page')  # get page number from query parameters

        if page_str:  # if page number is provided
            try:
                page = int(page_str)  # convert page number to integer
                if page < 0:  # if page number is negative, log error and return
                    logging.error(f"Invalid page number provided: {page}")
                    return func.HttpResponse(
                        body="Query parameter 'page' must be a non-negative integer.",
                        status_code=400
                    )
            except ValueError:  # if page number is not an integer, log error and return
                logging.error(f"Invalid page parameter provided: {page_str}")
                return func.HttpResponse(
                    body="Query parameter 'page' must be an integer.",
                    status_code=400
                )
        return page

    def queue_show_details(self, show_id_msg: dict[str, Any]) -> None:
        """Queue show details

        Args:
            show_id_msg (func.QueueMessage): Show ID message
        """
        self.storage_service.upload_queue_message(  # upload message to queue
            queue_name=DETAILS_QUEUE,  # queue name
            message=show_id_msg  # message to upload
        )

    def update_id_table(self, show_id: int, last_updated: int) -> None:
        """Update shows ID table

        Args:
            show_id (int): Show ID
            last_updated (str): Last updated
        """
        entity: dict[str, Any] = {
            "PartitionKey": "show",
            "RowKey": str(show_id),
            "LastUpdated": str(last_updated)
        }
        self.storage_service.upsert_entity(  # upsert entity in table for later season/episode retrieval
            table_name=SHOW_IDS_TABLE,  # table name
            entity=entity  # entity to upsert
        )
