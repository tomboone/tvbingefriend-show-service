"""Service for TV show-related operations."""
import json
import logging
from typing import Any

import azure.functions as func
from azure.storage.blob import ContainerClient, StorageStreamDownloader
from sqlalchemy.orm import Session
from tvbingefriend_azure_storage_service import StorageService  # type: ignore
from tvbingefriend_tvmaze_client.tvmaze_api import TVMazeAPI  # type: ignore

from tvbingefriend_show_service.config import (
    STORAGE_CONNECTION_STRING,
    SHOW_IDS_TABLE,
    SHOWS_PAGE_CONTAINER,
    SHOW_UPSERT_CONTAINER,
    SHOW_UPSERT_QUEUE,
    SHOWS_PAGE_QUEUE,
    SHOWS_INDEX_QUEUE
)
from tvbingefriend_show_service.repos.show_repo import ShowRepository


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
            queue_name=SHOWS_INDEX_QUEUE,  # queue name
            message=start_message  # message to upload
        )

        logging.info(f"ShowService.start_get_shows: Queued page {page} for retrieval")

    def get_shows_index_page(self, claim_ticket: func.QueueMessage) -> None:
        """Get one page of shows from TV Maze

        Args:
            claim_ticket (func.QueueMessage): Claim ticket
        """
        page_number: int | None = claim_ticket.get_json().get("page")  # get page number from message

        if page_number is None:  # if page number is missing, log error and return
            logging.error("Queue message is missing 'page' number.")
            return

        logging.info(f"ShowService.get_show_page: Getting shows from TV Maze for page_number: {page_number}")

        shows: list[dict[str, Any]] | None = self.tvmaze_api.get_shows(page_number)  # get one page from show index

        if shows:  # if shows are returned, upload data and queue claim ticket
            blob_name = f"shows_page_{page_number}.json"  # set shows blob name

            self.storage_service.upload_blob_data(  # upload shows blob
                container_name=SHOWS_PAGE_CONTAINER,  # container
                blob_name=blob_name,  # blob name
                data=shows  # shows data
            )

            self.storage_service.upload_queue_message(  # queue shows blob claim ticket
                queue_name=SHOWS_PAGE_QUEUE,  # queue name
                message={"blobe_name": blob_name}  # blob claim ticket
            )
            logging.info(f"Queued {len(shows)} shows from page {page_number} for processing in blob {blob_name}")

            self.storage_service.upload_queue_message(  # queue next page for retrieval
                queue_name=SHOWS_INDEX_QUEUE,  # queue name
                message={"page": page_number + 1}  # message to upload
            )
            logging.info(f"Queued page {page_number + 1} for retrieval")

    def queue_shows_for_upsert(self, claim_ticket: func.QueueMessage):
        """Queue shows for upsert

        Args:
            claim_ticket (func.QueueMessage): Claim ticket
        """
        shows: list[dict[str, Any]] | dict[str, Any] | None = self.get_blob_from_claim_ticket(  # get shows from ticket
            container=SHOWS_PAGE_CONTAINER,  # container
            claim_ticket=claim_ticket  # claim ticket
        )

        if not shows or not isinstance(shows, list):  # if shows are missing or not a list, log error and return
            logging.error("QueueService.queue_shows_for_upsert: Show list not found.")

        if isinstance(shows, list):  # if shows are a list
            for show in shows:  # for each show
                self.create_show_claim_ticket(show)  # queue show claim ticket

    def get_show_details(self, show_id_msg: func.QueueMessage) -> None:
        """Get show details

        Args:
            show_id_msg (func.QueueMessage): Claim ticket
        """
        show_id: int | None = show_id_msg.get_json().get("show_id")  # get show ID
        if show_id is None:  # if show ID is missing
            logging.error("Queue message is missing 'show_id' number.")
            return

        logging.info(f"ShowService.get_show_details: Getting show details for show_id: {show_id}")

        show: dict[str, Any] = self.tvmaze_api.get_show_details(show_id)
        if not show:
            logging.error(f"ShowService.get_show_details: Failed to get show ID {show_id}")
            return

        self.create_show_claim_ticket(show)

    def upsert_show(self, claim_ticket: func.QueueMessage, db: Session) -> None:
        """Upsert a show in the database

        Args:
            claim_ticket (func.QueueMessage): Claim ticket
            db (Session): Database session
        """
        show: dict[str, Any] | list[dict[str, Any]] | None = self.get_blob_from_claim_ticket(  # get show from ticket
            container=SHOW_UPSERT_CONTAINER,  # container
            claim_ticket=claim_ticket  # claim ticket
        )

        logging.info("ShowService.upsert_show: Upserting show")

        if not show or not isinstance(show, dict):
            logging.error("ShowService.upsert_show: Show not found.")
            return

        self.show_repository.upsert_show(show, db)  # upsert show

        self.update_id_table(
            show_id=show["id"],
            last_updated=show["updated"]
        )

    def get_updates(self, since: str = "day"):
        """Get updates

        Args:
            since (str): Since parameter for TV Maze API. Defaults to "day".
        """
        logging.info("ShowService.get_updates: Get updates")
        tvmaze_api: TVMazeAPI = TVMazeAPI()  # initialize TV Maze API client
        updates: dict[str, Any] = tvmaze_api.get_show_updates(period=since)  # get show updates

        for show_id, last_updated in updates.items():  # for each show update

            self.storage_service.upload_queue_message(  # queue show ID for upsert
                queue_name=SHOW_UPSERT_QUEUE,  # queue name
                message={"show_id": int(show_id)}  # queue message
            )

            self.update_id_table(  # update shows ID table
                show_id=int(show_id),
                last_updated=last_updated
            )

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

    def get_blob_from_claim_ticket(
            self, container: str, claim_ticket: func.QueueMessage
    ) -> list[dict[str, Any]] | dict[str, Any] | None:
        """Get blob from claim ticket

        Args:
            container (str): Container name
            claim_ticket (func.QueueMessage): Claim ticket

        Returns:
            list[dict[str, Any]] | dict[str, Any] | None: Blob data or None
        """
        message = claim_ticket.get_json()  # get claim ticket
        blob_name = message.get("blob_name")  # get blob name from claim

        if not blob_name:  # if blob name is missing
            logging.error("Queue message is missing 'blob_name' key.")
            return None

        container_client: ContainerClient = self.storage_service.get_blob_service_client(container)
        blob_bytes: StorageStreamDownloader[bytes] = container_client.get_blob_client(blob_name).download_blob()

        if not blob_bytes:
            logging.error(f"Blob {blob_name} not found in container {container}")
            return None

        blob: list[dict[str, Any]] | dict[str, Any] = json.loads(blob_bytes.readall())

        if not blob:
            logging.error(f"Blob {blob_name} is empty")
            return None

        return blob

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

    def create_show_claim_ticket(self, show: dict[str, Any]) -> None:
        """Create show claim ticket

        Args:
            show (dict[str, Any]): Show
        """
        show_id = show.get("id")
        blob_name = f"tv_show_{show_id}.json"

        self.storage_service.upload_blob_data(
            container_name=SHOW_UPSERT_CONTAINER,
            blob_name=blob_name,
            data=show
        )

        self.storage_service.upload_queue_message(
            queue_name=SHOW_UPSERT_QUEUE,
            message={"blob_name": blob_name}
        )

        logging.info(f"ShowService.create_show_claim_ticket: Queued show ID {show_id} for upsert")
