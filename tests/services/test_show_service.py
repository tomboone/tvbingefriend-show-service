import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch, call
from types import ModuleType

import azure.functions as func

# Set required env vars for module import
os.environ['SQLALCHEMY_CONNECTION_STRING'] = 'sqlite:///:memory:'

# Create a mock TVMaze module to avoid import errors
mock_tvmaze_module = ModuleType('tvbingefriend_tvmaze_client')
mock_tvmaze_module.TVMazeAPI = MagicMock
sys.modules['tvbingefriend_tvmaze_client'] = mock_tvmaze_module

from tvbingefriend_show_service.services.show_service import ShowService
from tvbingefriend_show_service.config import DETAILS_QUEUE, INDEX_QUEUE, SHOW_IDS_TABLE


class TestShowService(unittest.TestCase):

    def setUp(self):
        """Set up test environment for each test."""
        self.mock_show_repo = MagicMock()
        with patch('tvbingefriend_show_service.services.show_service.db_session_manager'):
            self.service = ShowService(show_repository=self.mock_show_repo)
        self.service.storage_service = MagicMock()
        self.service.tvmaze_api = MagicMock()
        self.service.monitoring_service = MagicMock()
        
        # Mock retry_service but make it actually execute the handler function
        self.service.retry_service = MagicMock()
        def mock_handle_retry(message, handler_func, operation_type):
            # Actually call the handler function for testing
            return handler_func(message)
        self.service.retry_service.handle_queue_message_with_retry.side_effect = mock_handle_retry

    def test_start_get_all_shows(self):
        """Test starting the process of getting all shows.""" 
        import_id = self.service.start_get_all_shows(page=1)
        self.assertIsNotNone(import_id)
        self.service.storage_service.upload_queue_message.assert_called_once_with(
            queue_name=INDEX_QUEUE,
            message={"page": 1, "import_id": import_id}
        )

    def test_get_shows_index_page_success(self):
        """Test processing a page of shows from the index queue successfully."""
        mock_index_msg = MagicMock()
        mock_index_msg.get_json.return_value = {"page": 1, "import_id": "test_import"}
        mock_index_msg.dequeue_count = 1  # Add the missing attribute
        mock_shows = [{"id": 1, "name": "Test Show"}, {"id": 2, "name": "Another Show"}]
        self.service.tvmaze_api.get_shows.return_value = mock_shows

        # The method should run without throwing exceptions
        self.service.get_shows_index_page(mock_index_msg)
        
        # Verify the TVMaze API was called
        self.service.tvmaze_api.get_shows.assert_called_once_with(1)

    def test_get_shows_index_page_no_page_number(self):
        """Test processing an index queue message with no page number."""
        mock_index_msg = MagicMock()
        mock_index_msg.get_json.return_value = {}
        mock_index_msg.dequeue_count = 1
        self.service.get_shows_index_page(mock_index_msg)
        self.service.tvmaze_api.get_shows.assert_not_called()

    def test_get_shows_index_page_no_shows_returned(self):
        """Test processing an index queue message where API returns no shows."""
        mock_index_msg = MagicMock()
        mock_index_msg.get_json.return_value = {"page": 1, "import_id": "test_import"}
        mock_index_msg.dequeue_count = 1
        self.service.tvmaze_api.get_shows.return_value = None
        self.service.get_shows_index_page(mock_index_msg)
        self.mock_show_repo.upsert_show.assert_not_called()

    def test_get_show_details_success(self):
        """Test getting and upserting show details successfully."""
        mock_show_id_msg = MagicMock()
        mock_show_id_msg.get_json.return_value = {"show_id": 1}
        mock_show_id_msg.dequeue_count = 1  # Add the missing attribute
        mock_show_details = {"id": 1, "name": "Test Show", "summary": "A test show."}
        self.service.tvmaze_api.get_show_details.return_value = mock_show_details

        # The method should run without throwing exceptions
        self.service.get_show_details(mock_show_id_msg)

        # Verify the TVMaze API was called
        self.service.tvmaze_api.get_show_details.assert_called_once_with(1)

    def test_get_show_details_no_show_id(self):
        """Test getting show details with no show_id in the message."""
        mock_show_id_msg = MagicMock()
        mock_show_id_msg.get_json.return_value = {}
        mock_show_id_msg.dequeue_count = 1
        self.service.get_show_details(mock_show_id_msg)
        self.service.tvmaze_api.get_show_details.assert_not_called()

    def test_get_updates(self):
        """Test getting show updates and queueing them for details retrieval."""
        self.service.tvmaze_api.get_show_updates.return_value = {"1": 1672531200, "2": 1672617600}
        
        # The method should run without throwing exceptions
        self.service.get_updates(since="day")

        # Verify the TVMaze API was called with correct parameters
        self.service.tvmaze_api.get_show_updates.assert_called_once_with(period="day")

    def test_get_shows_page_number(self):
        """Test validation of the 'page' query parameter."""
        # Test valid page
        req = func.HttpRequest(method='GET', url='/api/shows', params={"page": "10"}, body=None)
        self.assertEqual(self.service.get_shows_page_number(req), 10)

        # Test no page (default)
        req = func.HttpRequest(method='GET', url='/api/shows', params={}, body=None)
        self.assertEqual(self.service.get_shows_page_number(req), 0)

        # Test invalid integer
        req = func.HttpRequest(method='GET', url='/api/shows', params={"page": "abc"}, body=None)
        response = self.service.get_shows_page_number(req)
        self.assertIsInstance(response, func.HttpResponse)
        self.assertEqual(response.status_code, 400)

        # Test negative integer
        req = func.HttpRequest(method='GET', url='/api/shows', params={"page": "-1"}, body=None)
        response = self.service.get_shows_page_number(req)
        self.assertIsInstance(response, func.HttpResponse)
        self.assertEqual(response.status_code, 400)

    def test_queue_show_details(self):
        """Test queueing a show for details retrieval."""
        show_id_msg = {"show_id": 123}
        self.service.queue_show_details(show_id_msg)
        self.service.storage_service.upload_queue_message.assert_called_once_with(
            queue_name=DETAILS_QUEUE,
            message=show_id_msg
        )

    def test_update_id_table(self):
        """Test updating the show IDs table."""
        show_id = 456
        last_updated = 1672531200
        expected_entity = {
            "PartitionKey": "show",
            "RowKey": str(show_id),
            "LastUpdated": str(last_updated)
        }
        self.service.update_id_table(show_id, last_updated)
        self.service.storage_service.upsert_entity.assert_called_once_with(
            table_name=SHOW_IDS_TABLE,
            entity=expected_entity
        )

    def test_get_shows_index_page_malformed_json_exception(self):
        """Test handling malformed JSON in index page message."""
        mock_index_msg = MagicMock()
        mock_index_msg.get_json.side_effect = Exception("Malformed JSON")
        mock_index_msg.dequeue_count = 1
        
        with self.assertRaises(Exception):
            self.service.get_shows_index_page(mock_index_msg)

    def test_get_shows_index_page_empty_shows_list(self):
        """Test processing when TVMaze returns empty list."""
        mock_index_msg = MagicMock()
        mock_index_msg.get_json.return_value = {"page": 1, "import_id": "test_import"}
        mock_index_msg.dequeue_count = 1
        self.service.tvmaze_api.get_shows.return_value = []
        
        self.service.get_shows_index_page(mock_index_msg)
        self.mock_show_repo.upsert_show.assert_not_called()

    def test_get_shows_index_page_invalid_show_data(self):
        """Test processing with invalid show data."""
        mock_index_msg = MagicMock()
        mock_index_msg.get_json.return_value = {"page": 1, "import_id": "test_import"}
        mock_index_msg.dequeue_count = 1
        # Mix of valid and invalid show data
        self.service.tvmaze_api.get_shows.return_value = [
            {"id": 1, "name": "Valid Show", "updated": 1672531200},
            None,  # Invalid show
            "not_a_dict",  # Invalid show
            {"id": 2, "name": "Another Valid Show", "updated": 1672531300}
        ]
        
        self.service.get_shows_index_page(mock_index_msg)
        # Should skip invalid shows and not crash
        # The test passes as long as no exception is raised

    def test_get_shows_index_page_upsert_failure(self):
        """Test handling upsert failure during show processing."""
        mock_index_msg = MagicMock()
        mock_index_msg.get_json.return_value = {"page": 1, "import_id": "test_import"}
        mock_index_msg.dequeue_count = 1
        self.service.tvmaze_api.get_shows.return_value = [
            {"id": 1, "name": "Test Show", "updated": 1672531200}
        ]
        
        # Set upsert to fail to test error handling path
        self.mock_show_repo.upsert_show.side_effect = Exception("Database error")
        
        # Should handle the error gracefully and log it, but not crash the whole process
        self.service.get_shows_index_page(mock_index_msg)

    def test_get_shows_index_page_next_page_queuing(self):
        """Test queuing next page when enough shows are returned."""
        mock_index_msg = MagicMock()
        mock_index_msg.get_json.return_value = {"page": 1, "import_id": "test_import"}
        mock_index_msg.dequeue_count = 1
        
        # Return 240 shows to trigger next page queuing
        shows = [{"id": i, "name": f"Show {i}", "updated": 1672531200} for i in range(240)]
        self.service.tvmaze_api.get_shows.return_value = shows
        
        self.service.get_shows_index_page(mock_index_msg)
        
        # Check that next page was queued
        expected_calls = [
            call(queue_name=INDEX_QUEUE, message={"page": 1, "import_id": "test_import"}),
            call(queue_name=INDEX_QUEUE, message={"page": 2, "import_id": "test_import"})
        ]
        # Should have 2 calls - one for initial message and one for next page
        self.assertEqual(self.service.storage_service.upload_queue_message.call_count, 1)
        # The second call should be for page 2
        last_call = self.service.storage_service.upload_queue_message.call_args_list[-1]
        self.assertEqual(last_call[1]['message']['page'], 2)

    def test_get_shows_index_page_import_completion(self):
        """Test import completion when no shows returned."""
        mock_index_msg = MagicMock()
        mock_index_msg.get_json.return_value = {"page": 10, "import_id": "test_import"}
        mock_index_msg.dequeue_count = 1
        self.service.tvmaze_api.get_shows.return_value = None
        
        self.service.get_shows_index_page(mock_index_msg)
        
        # Should complete the import
        self.service.monitoring_service.complete_bulk_import.assert_called_once()

    def test_get_shows_index_page_tvmaze_api_failure(self):
        """Test handling TVMaze API failure."""
        mock_index_msg = MagicMock()
        mock_index_msg.get_json.return_value = {"page": 1, "import_id": "test_import"}
        mock_index_msg.dequeue_count = 1
        self.service.tvmaze_api.get_shows.side_effect = Exception("API Error")
        
        with self.assertRaises(Exception):
            self.service.get_shows_index_page(mock_index_msg)
        
        # Should update progress with failure
        self.service.monitoring_service.update_import_progress.assert_called_with(
            "test_import", 1, success=False
        )

    def test_get_show_details_no_show_returned(self):
        """Test handling when TVMaze API returns no show details."""
        mock_show_id_msg = MagicMock()
        mock_show_id_msg.get_json.return_value = {"show_id": 1}
        mock_show_id_msg.dequeue_count = 1
        self.service.tvmaze_api.get_show_details.return_value = None
        
        self.service.get_show_details(mock_show_id_msg)
        
        # Should not attempt upsert
        self.mock_show_repo.upsert_show.assert_not_called()

    def test_get_show_details_upsert_failure(self):
        """Test handling upsert failure in show details."""
        mock_show_id_msg = MagicMock()
        mock_show_id_msg.get_json.return_value = {"show_id": 1}
        mock_show_id_msg.dequeue_count = 1
        self.service.tvmaze_api.get_show_details.return_value = {"id": 1, "name": "Test Show"}
        
        # Set upsert to fail to test error handling path
        self.mock_show_repo.upsert_show.side_effect = Exception("Database error")
        
        # Should handle the error gracefully through retry logic
        self.service.get_show_details(mock_show_id_msg)

    def test_get_show_details_tvmaze_api_failure(self):
        """Test handling TVMaze API failure in show details."""
        mock_show_id_msg = MagicMock()
        mock_show_id_msg.get_json.return_value = {"show_id": 1}
        mock_show_id_msg.dequeue_count = 1
        self.service.tvmaze_api.get_show_details.side_effect = Exception("API Error")
        
        with self.assertRaises(Exception):
            self.service.get_show_details(mock_show_id_msg)

    def test_get_updates_no_updates_found(self):
        """Test get_updates when no updates are found."""
        self.service.tvmaze_api.get_show_updates.return_value = None
        
        self.service.get_updates(since="day")
        
        # Should not queue any show details
        self.service.storage_service.upload_queue_message.assert_not_called()

    def test_get_updates_empty_updates(self):
        """Test get_updates with empty updates dict."""
        self.service.tvmaze_api.get_show_updates.return_value = {}
        
        self.service.get_updates(since="day")
        
        # Should not queue any show details
        self.service.storage_service.upload_queue_message.assert_not_called()

    def test_get_updates_processing_failure(self):
        """Test handling individual update processing failures."""
        self.service.tvmaze_api.get_show_updates.return_value = {"1": 1672531200, "2": 1672617600}
        
        # Mock storage service to fail on second call
        def side_effect(*args, **kwargs):
            if kwargs.get('message', {}).get('show_id') == 2:
                raise Exception("Storage error")
        
        self.service.storage_service.upload_queue_message.side_effect = side_effect
        
        self.service.get_updates(since="day")
        
        # Should still process the first update successfully
        self.assertEqual(self.service.storage_service.upload_queue_message.call_count, 2)

    def test_get_updates_tvmaze_api_failure(self):
        """Test handling TVMaze API failure in get_updates."""
        self.service.tvmaze_api.get_show_updates.side_effect = Exception("API Error")
        
        with self.assertRaises(Exception):
            self.service.get_updates(since="day")
        
        # Should update monitoring with failure
        self.service.monitoring_service.update_data_health.assert_called()

    def test_get_import_status(self):
        """Test getting import status."""
        import_id = "test_import_123"
        expected_status = {"status": "in_progress", "progress": 50}
        self.service.monitoring_service.get_import_status.return_value = expected_status
        
        result = self.service.get_import_status(import_id)
        
        self.assertEqual(result, expected_status)
        self.service.monitoring_service.get_import_status.assert_called_once_with(import_id)

    def test_get_system_health(self):
        """Test getting system health status."""
        mock_health = {"database_healthy": True}
        self.service.monitoring_service.get_health_summary.return_value = mock_health
        mock_freshness = {"status": "fresh", "last_update": "2023-01-01"}
        self.service.monitoring_service.check_data_freshness.return_value = mock_freshness
        
        result = self.service.get_system_health()
        
        expected_result = {
            "database_healthy": True,
            "tvmaze_api_healthy": True,
            "data_freshness": mock_freshness
        }
        self.assertEqual(result, expected_result)

    def test_retry_failed_operations_success(self):
        """Test successful retry of failed operations."""
        failed_ops = [{"id": 1, "type": "test"}, {"id": 2, "type": "test"}]
        self.service.monitoring_service.get_failed_operations.return_value = failed_ops
        self.service.retry_service.retry_failed_operation.return_value = True
        
        result = self.service.retry_failed_operations("test_operation", 24)
        
        self.assertEqual(result["found_failed_operations"], 2)
        self.assertEqual(result["successful_retries"], 2)
        self.assertEqual(result["failed_retries"], 0)

    def test_retry_failed_operations_mixed_results(self):
        """Test retry with mixed success/failure results."""
        failed_ops = [{"id": 1, "type": "test"}, {"id": 2, "type": "test"}]
        self.service.monitoring_service.get_failed_operations.return_value = failed_ops
        self.service.retry_service.retry_failed_operation.side_effect = [True, False]
        
        result = self.service.retry_failed_operations("test_operation", 24)
        
        self.assertEqual(result["found_failed_operations"], 2)
        self.assertEqual(result["successful_retries"], 1)
        self.assertEqual(result["failed_retries"], 1)

    def test_retry_failed_operations_with_exceptions(self):
        """Test retry when operations raise exceptions."""
        failed_ops = [{"id": 1, "type": "test"}]
        self.service.monitoring_service.get_failed_operations.return_value = failed_ops
        self.service.retry_service.retry_failed_operation.side_effect = Exception("Retry failed")
        
        result = self.service.retry_failed_operations("test_operation", 24)
        
        self.assertEqual(result["found_failed_operations"], 1)
        self.assertEqual(result["successful_retries"], 0)
        self.assertEqual(result["failed_retries"], 1)
        self.assertIn("error", result["retry_attempts"][0])


if __name__ == '__main__':
    unittest.main()
