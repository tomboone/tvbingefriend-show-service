import json
import os
import unittest
from unittest.mock import MagicMock, patch, call

import azure.functions as func

# Set required env vars for module import
os.environ['DB_HOST'] = 'test_host'
os.environ['DB_NAME'] = 'test_db'
os.environ['DB_USER'] = 'test_user'
os.environ['SQLALCHEMY_CONNECTION_STRING'] = 'sqlite:///:memory:'

from tvbingefriend_show_service.services.show_service import ShowService
from tvbingefriend_show_service.config import SHOW_DETAILS_QUEUE, SHOWS_INDEX_QUEUE, SHOW_IDS_TABLE


class TestShowService(unittest.TestCase):

    def setUp(self):
        """Set up test environment for each test."""
        self.mock_show_repo = MagicMock()
        with patch('tvbingefriend_show_service.services.show_service.db_session_manager'):
            self.service = ShowService(show_repository=self.mock_show_repo)
        self.service.storage_service = MagicMock()
        self.service.tvmaze_api = MagicMock()

    def test_start_get_all_shows(self):
        """Test starting the process of getting all shows."""
        self.service.start_get_all_shows(page=1)
        self.service.storage_service.upload_queue_message.assert_called_once_with(
            queue_name=SHOWS_INDEX_QUEUE,
            message={"page": 1}
        )

    @patch('tvbingefriend_show_service.services.show_service.db_session_manager')
    def test_get_shows_index_page_success(self, mock_db_session_manager):
        """Test processing a page of shows from the index queue successfully."""
        mock_index_msg = func.QueueMessage(body=json.dumps({"page": 1}).encode('utf-8'))
        mock_shows = [{"id": 1, "name": "Test Show"}, {"id": 2, "name": "Another Show"}]
        self.service.tvmaze_api.get_shows.return_value = mock_shows

        self.service.get_shows_index_page(mock_index_msg)

        self.service.tvmaze_api.get_shows.assert_called_once_with(1)
        self.assertEqual(self.mock_show_repo.upsert_show.call_count, 2)
        self.mock_show_repo.upsert_show.assert_has_calls([
            call(mock_shows[0], mock_db_session_manager.return_value.__enter__.return_value),
            call(mock_shows[1], mock_db_session_manager.return_value.__enter__.return_value)
        ])

    def test_get_shows_index_page_no_page_number(self):
        """Test processing an index queue message with no page number."""
        mock_index_msg = func.QueueMessage(body=json.dumps({}).encode('utf-8'))
        self.service.get_shows_index_page(mock_index_msg)
        self.service.tvmaze_api.get_shows.assert_not_called()

    def test_get_shows_index_page_no_shows_returned(self):
        """Test processing an index queue message where API returns no shows."""
        mock_index_msg = func.QueueMessage(body=json.dumps({"page": 1}).encode('utf-8'))
        self.service.tvmaze_api.get_shows.return_value = None
        self.service.get_shows_index_page(mock_index_msg)
        self.mock_show_repo.upsert_show.assert_not_called()

    @patch('tvbingefriend_show_service.services.show_service.db_session_manager')
    def test_get_show_details_success(self, mock_db_session_manager):
        """Test getting and upserting show details successfully."""
        mock_show_id_msg = func.QueueMessage(body=json.dumps({"show_id": 1}).encode('utf-8'))
        mock_show_details = {"id": 1, "name": "Test Show", "summary": "A test show."}
        self.service.tvmaze_api.get_show_details.return_value = mock_show_details

        self.service.get_show_details(mock_show_id_msg)

        self.service.tvmaze_api.get_show_details.assert_called_once_with(1)
        self.mock_show_repo.upsert_show.assert_called_once_with(
            mock_show_details, mock_db_session_manager.return_value.__enter__.return_value
        )

    def test_get_show_details_no_show_id(self):
        """Test getting show details with no show_id in the message."""
        mock_show_id_msg = func.QueueMessage(body=json.dumps({}).encode('utf-8'))
        self.service.get_show_details(mock_show_id_msg)
        self.service.tvmaze_api.get_show_details.assert_not_called()

    @patch('tvbingefriend_show_service.services.show_service.TVMazeAPI')
    def test_get_updates(self, mock_tvmaze_api_class):
        """Test getting show updates and queueing them for details retrieval."""
        mock_api_instance = MagicMock()
        mock_api_instance.get_show_updates.return_value = {"1": 1672531200, "2": 1672617600}
        mock_tvmaze_api_class.return_value = mock_api_instance
        self.service.queue_show_details = MagicMock()
        self.service.update_id_table = MagicMock()

        self.service.get_updates(since="day")

        mock_api_instance.get_show_updates.assert_called_once_with(period="day")
        self.assertEqual(self.service.queue_show_details.call_count, 2)
        self.service.queue_show_details.assert_has_calls([
            call({"show_id": 1}),
            call({"show_id": 2})
        ])
        self.assertEqual(self.service.update_id_table.call_count, 2)
        self.service.update_id_table.assert_has_calls([
            call(1, 1672531200),
            call(2, 1672617600)
        ])

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
            queue_name=SHOW_DETAILS_QUEUE,
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
