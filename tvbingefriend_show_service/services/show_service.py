"""Service for TV show-related operations."""
import logging
from datetime import datetime, UTC
from typing import Any
import uuid

import azure.functions as func
from tvbingefriend_azure_storage_service import StorageService  # type: ignore
from tvbingefriend_tvmaze_client import TVMazeAPI  # type: ignore

from tvbingefriend_show_service.config import (
    STORAGE_CONNECTION_STRING,
    DETAILS_QUEUE,
    SHOW_IDS_TABLE,
    INDEX_QUEUE
)
from tvbingefriend_show_service.models.show import Show
from tvbingefriend_show_service.repos.show_repo import ShowRepository
from tvbingefriend_show_service.utils import db_session_manager
from tvbingefriend_show_service.services.monitoring_service import MonitoringService, ImportStatus
from tvbingefriend_show_service.services.retry_service import RetryService


# noinspection PyMethodMayBeStatic
class ShowService:
    """Service for TV show-related operations."""
    def __init__(self, 
                 show_repository: ShowRepository | None = None,
                 monitoring_service: MonitoringService | None = None,
                 retry_service: RetryService | None = None) -> None:
        self.show_repository = show_repository or ShowRepository()
        self.storage_service = StorageService(STORAGE_CONNECTION_STRING)
        
        # Use TVMaze client
        self.tvmaze_api = TVMazeAPI()
        
        # Initialize monitoring services (keep retry service for non-TVMaze operations)
        self.monitoring_service = monitoring_service or MonitoringService()
        self.retry_service = retry_service or RetryService()
        
        # Current bulk import ID for tracking
        self.current_import_id: str | None = None

    def start_get_all_shows(self, page: int = 0, estimated_pages: int | None = None) -> str:
        """Start get all shows from TV Maze with progress tracking.

        Args:
            page (int): Page number to start from. Defaults to 0.
            estimated_pages (int | None): Estimated total pages for progress tracking.
            
        Returns:
            Import ID for tracking progress
        """
        # Generate unique import ID
        import_id = f"bulk_import_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
        self.current_import_id = import_id
        
        logging.info(
            f"ShowService.start_get_shows: Starting show retrieval from page {page} with import ID: {import_id}"
        )

        # Start tracking this bulk import
        self.monitoring_service.start_bulk_import_tracking(
            import_id=import_id,
            start_page=page,
            estimated_pages=estimated_pages
        )

        start_message: dict[str, Any] = {
            "page": page,
            "import_id": import_id  # Include import ID for progress tracking
        }

        self.storage_service.upload_queue_message(
            queue_name=INDEX_QUEUE,
            message=start_message
        )

        logging.info(f"ShowService.start_get_shows: Queued page {page} for retrieval with import ID: {import_id}")
        return import_id

    def get_shows_index_page(self, indexmsg: func.QueueMessage) -> None:
        """Get one page of shows from TV Maze with retry logic and progress tracking.

        Args:
            indexmsg (func.QueueMessage): Page index message
        """
        logging.info("=== ShowService.get_shows_index_page ENTRY ===")
        
        # Handle message with retry logic
        def handle_index_page(message: func.QueueMessage) -> None:
            """Handle index page."""
            logging.info("=== handle_index_page ENTRY ===")
            try:
                msg_data = message.get_json()
                logging.info(f"Message data in handle_index_page: {msg_data}")
                page_number: int | None = msg_data.get("page")
                import_id: str | None = msg_data.get("import_id")
                logging.info(f"Extracted page_number: {page_number}, import_id: {import_id}")

                if page_number is None:
                    logging.error("Queue message is missing 'page' number.")
                    return

                logging.info(f"ShowService.get_show_page: Getting shows from TV Maze for page_number: {page_number}")
            except Exception as err:
                logging.error(f"Error in handle_index_page setup: {err}", exc_info=True)
                raise

            try:
                logging.info(f"Calling TVMaze API for page {page_number}...")
                # TVMaze API now has built-in rate limiting and retry logic
                shows: list[dict[str, Any]] | None = self.tvmaze_api.get_shows(page_number)
                logging.info(f"TVMaze API returned {len(shows) if shows else 0} shows for page {page_number}")

                if shows:
                    # Process shows with database retry logic
                    success_count = 0
                    for show in shows:
                        if not show or not isinstance(show, dict):
                            logging.error("ShowService.upsert_show: Show not found.")
                            continue
                        
                        @self.retry_service.with_retry('database_write', max_attempts=3)
                        def upsert_with_retry():
                            """Upsert shows into database."""
                            with db_session_manager() as db:
                                self.show_repository.upsert_show(show, db)
                        
                        try:
                            upsert_with_retry()
                            
                            # Update ID table for show tracking
                            show_id = show.get('id')
                            show_updated = show.get('updated')
                            if show_id and show_updated:
                                @self.retry_service.with_retry('storage_write', max_attempts=3)
                                def update_id_table_with_retry():
                                    """Update show ID table."""
                                    self.update_id_table(int(show_id), int(show_updated))
                                
                                update_id_table_with_retry()
                            
                            success_count += 1
                        except Exception as err:
                            logging.error(f"Failed to upsert show {show.get('id', 'unknown')} after retries: {err}")

                    logging.info(f"Successfully processed {success_count}/{len(shows)} shows from page {page_number}")
                    
                    # Update progress tracking
                    if import_id:
                        self.monitoring_service.update_import_progress(import_id, page_number)
                    
                    # Queue next page if we got a substantial number of shows (indicates more pages available)
                    if len(shows) >= 200:  # TVMaze typically returns 240+ shows per page when more are available
                        next_page = page_number + 1
                        next_page_message = {
                            "page": next_page,
                            "import_id": import_id
                        }
                        logging.info(f"Queuing next page {next_page} for processing")
                        self.storage_service.upload_queue_message(
                            queue_name=INDEX_QUEUE,
                            message=next_page_message
                        )
                else:
                    logging.info(f"No shows returned for page {page_number} - may have reached the end")
                    if import_id:
                        self.monitoring_service.complete_bulk_import(import_id, ImportStatus.COMPLETED)

            except Exception as err:
                logging.error(f"Failed to get shows for page {page_number}: {err}")
                if import_id:
                    self.monitoring_service.update_import_progress(import_id, page_number, success=False)
                raise

        # Process with retry logic
        logging.info("=== Calling retry_service.handle_queue_message_with_retry ===")
        try:
            self.retry_service.handle_queue_message_with_retry(
                message=indexmsg,
                handler_func=handle_index_page,
                operation_type="index_page"
            )
            logging.info("=== retry_service.handle_queue_message_with_retry COMPLETED ===")
        except Exception as e:
            logging.error(f"=== ERROR in retry_service.handle_queue_message_with_retry: {e} ===", exc_info=True)
            raise

    def get_show_details(self, show_id_msg: func.QueueMessage) -> None:
        """Get show details with retry logic and rate limiting.

        Args:
            show_id_msg (func.QueueMessage): Show ID message
        """
        def handle_show_details(message: func.QueueMessage) -> None:
            """Handle show details message."""
            show_id: int | None = message.get_json().get("show_id")
            if show_id is None:
                logging.error("Queue message is missing 'show_id' number.")
                return

            try:
                # TVMaze API now has built-in rate limiting and retry logic
                show: dict[str, Any] = self.tvmaze_api.get_show_details(show_id)
                if not show:
                    logging.error(f"ShowService.get_show_details: Failed to get show ID {show_id}")
                    return

                # Use database retry logic
                @self.retry_service.with_retry('database_write', max_attempts=3)
                def upsert_with_retry():
                    """Upsert show details."""
                    with db_session_manager() as db:
                        self.show_repository.upsert_show(show, db)

                upsert_with_retry()
                logging.info(f"Successfully processed show details for ID {show_id}")

            except Exception as e:
                logging.error(f"Failed to get/store show details for ID {show_id}: {e}")
                raise

        # Process with retry logic
        self.retry_service.handle_queue_message_with_retry(
            message=show_id_msg,
            handler_func=handle_show_details,
            operation_type="show_details"
        )

    def get_updates(self, since: str = "day"):
        """Get updates with rate limiting and monitoring.

        Args:
            since (str): Since parameter for TV Maze API. Defaults to "day".
        """
        logging.info(f"ShowService.get_updates: Getting updates since {since}")
        
        try:
            # TVMaze API now has built-in rate limiting and retry logic
            updates: dict[str, Any] = self.tvmaze_api.get_show_updates(period=since)
            
            if not updates:
                logging.info("No updates found")
                return
            
            logging.info(f"Found {len(updates)} show updates")
            
            # Process updates
            success_count = 0
            for show_id, last_updated in updates.items():
                try:
                    details_queue_msg = {
                        "show_id": int(show_id),
                    }
                    self.queue_show_details(details_queue_msg)
                    
                    # Update ID table with retry logic
                    @self.retry_service.with_retry('storage_write', max_attempts=3)
                    def update_id_table_with_retry():
                        """Upsert show updates."""
                        self.update_id_table(int(show_id), int(last_updated))
                    
                    update_id_table_with_retry()
                    success_count += 1
                    
                except Exception as e:
                    logging.error(f"Failed to process update for show {show_id}: {e}")
            
            logging.info(f"Successfully queued {success_count}/{len(updates)} show updates")
            
            # Update data health metrics
            self.monitoring_service.update_data_health(
                metric_name="updates_processed",
                value=success_count,
                threshold=len(updates) * 0.95  # Alert if less than 95% success rate
            )
            
        except Exception as e:
            logging.error(f"Failed to get show updates: {e}")
            self.monitoring_service.update_data_health(
                metric_name="updates_failed",
                value=1
            )
            raise

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
    
    def get_import_status(self, import_id: str) -> dict[str, Any]:
        """Get the status of a bulk import operation.
        
        Args:
            import_id: Import operation identifier
            
        Returns:
            Dictionary with import status information
        """
        return self.monitoring_service.get_import_status(import_id)
    
    def get_system_health(self) -> dict[str, Any]:
        """Get overall system health status.
        
        Returns:
            Dictionary with system health information
        """
        health_summary = self.monitoring_service.get_health_summary()
        
        # TVMaze API status (basic connectivity assumed)
        health_summary['tvmaze_api_healthy'] = True  # Assume healthy for standard client
        
        # Add data freshness check
        freshness_status = self.monitoring_service.check_data_freshness()
        health_summary['data_freshness'] = freshness_status
        
        return health_summary
    
    def retry_failed_operations(self, operation_type: str, max_age_hours: int = 24) -> dict[str, Any]:
        """Retry failed operations of a specific type.
        
        Args:
            operation_type: Type of operations to retry
            max_age_hours: Only retry failures within this many hours
            
        Returns:
            Summary of retry attempts
        """
        failed_operations = self.monitoring_service.get_failed_operations(operation_type, max_age_hours)
        
        retry_summary: dict[str, Any] = {
            'operation_type': operation_type,
            'found_failed_operations': len(failed_operations),
            'successful_retries': 0,
            'failed_retries': 0,
            'retry_attempts': []
        }
        
        for operation in failed_operations:
            try:
                success = self.retry_service.retry_failed_operation(operation_type, operation)
                if success:
                    retry_summary['successful_retries'] += 1
                else:
                    retry_summary['failed_retries'] += 1
                
                retry_summary['retry_attempts'].append({
                    'operation': operation,
                    'success': success
                })
                
            except Exception as e:
                logging.error(f"Failed to retry operation {operation}: {e}")
                retry_summary['failed_retries'] += 1
                retry_summary['retry_attempts'].append({
                    'operation': operation,
                    'success': False,
                    'error': str(e)
                })
        
        return retry_summary

    def get_show_by_id(self, show_id: int) -> dict[str, Any] | None:
        """Get a show by its ID

        Args:
            show_id (int): Show ID

        Returns:
            dict[str, Any] | None: Show data or None if not found
        """
        try:
            with db_session_manager() as db:
                show = self.show_repository.get_show_by_id(show_id, db)
                if show:
                    # Convert Show object to dictionary
                    show_dict = {
                        'id': show.id,
                        'url': show.url,
                        'name': show.name,
                        'type': show.type,
                        'language': show.language,
                        'genres': show.genres,
                        'status': show.status,
                        'runtime': show.runtime,
                        'averageRuntime': show.averageRuntime,
                        'premiered': show.premiered,
                        'ended': show.ended,
                        'officialSite': show.officialSite,
                        'schedule': show.schedule,
                        'rating': show.rating,
                        'weight': show.weight,
                        'network': show.network,
                        'webchannel': show.webchannel,
                        'dvdCountry': show.dvdCountry,
                        'externals': show.externals,
                        'image': show.image,
                        'summary': show.summary,
                        'updated': show.updated,
                        '_links': show._links
                    }
                    return show_dict
                return None
        except Exception as e:
            logging.error(f"ShowService.get_show_by_id: Error getting show {show_id}: {e}")
            return None

    def search_shows(self, query: str, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
        """Search shows with optimized query and serialization

        Args:
            query (str): Search query string
            limit (int): Maximum number of results to return (default 20)
            offset (int): Number of results to skip for pagination (default 0)

        Returns:
            list[dict[str, Any]]: List of matching show data ordered by relevance
        """
        try:
            with db_session_manager() as db:
                shows = self.show_repository.search_shows(query, limit, offset, db)

                # Optimized serialization for search results (include only essential fields)
                return [
                    {
                        'id': show.id,
                        'name': show.name,
                        'type': show.type,
                        'language': show.language,
                        'genres': show.genres,
                        'status': show.status,
                        'premiered': show.premiered,
                        'ended': show.ended,
                        'rating': show.rating,
                        'weight': show.weight,
                        'network': show.network,
                        'webchannel': show.webchannel,
                        'image': show.image,
                        'summary': show.summary[:200] + '...' if show.summary and len(show.summary) > 200 else show.summary
                    }
                    for show in shows
                ]
        except Exception as e:
            logging.error(f"ShowService.search_shows: Error searching for '{query}': {e}")
            return []

    def get_shows_bulk(self, offset: int | None = 0, limit: int | None = 100) -> list[dict[str, Any]]:
        """Get shows bulk
        Args:
            offset (int): Number of results to skip for pagination (default 0)
            limit (int): Maximum number of results to return (default 100)

        Returns:
            list[dict[str, Any]]: List of show data ordered by id
        """
        try:
            with db_session_manager() as db:
                shows_bulk: list[Show] = self.show_repository.get_shows_bulk(db, offset, limit)

                # noinspection PyProtectedMember
                return [
                    {
                        "id": show.id,
                        "url": show.url,
                        "name": show.name,
                        "type": show.type,
                        "language": show.language,
                        "genres": show.genres,
                        "status": show.status,
                        "runtime": show.runtime,
                        "averageRuntime": show.averageRuntime,
                        "premiered": show.premiered,
                        "ended": show.ended,
                        "officialSite": show.officialSite,
                        "schedule": show.schedule,
                        "rating": show.rating,
                        "weight": show.weight,
                        "network": show.network,
                        "webchannel": show.webchannel,
                        "dvdCountry": show.dvdCountry,
                        "externals": show.externals,
                        "image": show.image,
                        "summary": show.summary,
                        "updated": show.updated,
                        "_links": show._links
                    }
                    for show in shows_bulk
                ]
        except Exception as e:
            logging.error(f"ShowService.get_shows_bulk: Error getting shows bulk: {e}")
            return []

    def get_show_summaries(self, offset: int | None = 0, limit: int | None = 100) -> list[dict[str, Any]]:
        """Get shows summaries

        Args:
            offset (int): Number of results to skip for pagination (default 0)
            limit (int): Maximum number of results to return (default 100)

        Returns:
            list[dict[str, Any]]: List of show data ordered by id
        """
        try:
            with db_session_manager() as db:
                shows_bulk: list[Show] = self.show_repository.get_shows_bulk(db, offset, limit)
                return [
                    {
                        "id": show.id,
                        "name": show.name,
                        "genres": show.genres,
                        "summary": show.summary,
                        "rating": show.rating,
                        "network": show.network,
                        "webchannel": show.webchannel,
                        "type": show.type,
                        "language": show.language
                    }
                    for show in shows_bulk
                ]
        except Exception as e:
            logging.error(f"ShowService.get_shows_summaries: Error getting show summaries: {e}")
            return []
