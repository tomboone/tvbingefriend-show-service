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


if __name__ == '__main__':
    unittest.main()
