import json
import os
import unittest
from unittest.mock import MagicMock, patch

import azure.functions as func

# Set required env var for module import
os.environ['SQLALCHEMY_CONNECTION_STRING'] = 'sqlite:///:memory:'

from tvbingefriend_show_service.services.show_service import ShowService


class TestShowService(unittest.TestCase):

    def setUp(self):
        self.mock_show_repo = MagicMock()
        self.service = ShowService(show_repository=self.mock_show_repo)
        self.service.storage_service = MagicMock()
        self.service.tvmaze_api = MagicMock()

    def test_start_get_all_shows(self):
        self.service.start_get_all_shows(page=1)
        self.service.storage_service.upload_queue_message.assert_called_once_with(
            queue_name='index-queue',
            message={"page": 1}
        )

    def test_get_shows_index_page(self):
        mock_claim_ticket = func.QueueMessage(body=json.dumps({"page": 1}).encode('utf-8'))
        self.service.tvmaze_api.get_shows.return_value = [{"id": 1, "name": "Test Show"}]

        self.service.get_shows_index_page(mock_claim_ticket)

        self.service.storage_service.upload_blob_data.assert_called_once()
        self.assertEqual(self.service.storage_service.upload_queue_message.call_count, 2)

    def test_get_shows_index_page_no_shows(self):
        mock_claim_ticket = func.QueueMessage(body=json.dumps({"page": 1}).encode('utf-8'))
        self.service.tvmaze_api.get_shows.return_value = None

        self.service.get_shows_index_page(mock_claim_ticket)

        self.service.storage_service.upload_blob_data.assert_not_called()

    @patch('tvbingefriend_show_service.services.show_service.ShowService.get_blob_from_claim_ticket')
    def test_queue_shows_for_upsert(self, mock_get_blob):
        mock_get_blob.return_value = [{"id": 1, "name": "Test Show"}]
        mock_claim_ticket = func.QueueMessage(body=json.dumps({"blob_name": "test.json"}).encode('utf-8'))

        self.service.queue_shows_for_upsert(mock_claim_ticket)

        self.service.storage_service.upload_blob_data.assert_called_once()
        self.service.storage_service.upload_queue_message.assert_called_once()

    def test_get_show_details(self):
        mock_show_id_msg = func.QueueMessage(body=json.dumps({"show_id": 1}).encode('utf-8'))
        self.service.tvmaze_api.get_show_details.return_value = {"id": 1, "name": "Test Show"}

        self.service.get_show_details(mock_show_id_msg)

        self.service.storage_service.upload_blob_data.assert_called_once()
        self.service.storage_service.upload_queue_message.assert_called_once()

    @patch('tvbingefriend_show_service.services.show_service.ShowService.get_blob_from_claim_ticket')
    def test_upsert_show(self, mock_get_blob):
        mock_get_blob.return_value = {"id": 1, "name": "Test Show", "updated": "2024-01-01"}
        mock_claim_ticket = func.QueueMessage(body=json.dumps({"blob_name": "test.json"}).encode('utf-8'))
        mock_db_session = MagicMock()

        self.service.upsert_show(mock_claim_ticket, mock_db_session)

        self.mock_show_repo.upsert_show.assert_called_once()
        self.service.storage_service.upsert_entity.assert_called_once()

    @patch('tvbingefriend_show_service.services.show_service.TVMazeAPI')
    def test_get_updates(self, mock_tvmaze_api_class):
        mock_api_instance = MagicMock()
        mock_api_instance.get_show_updates.return_value = {"1": "2024-01-01"}
        mock_tvmaze_api_class.return_value = mock_api_instance

        self.service.get_updates()

        self.service.storage_service.upload_queue_message.assert_called_once_with(
            queue_name='shows-upsert-queue',
            message={'show_id': 1}
        )
        self.service.storage_service.upsert_entity.assert_called_once_with(
            table_name='shows-ids-table',
            entity={
                'PartitionKey': 'show',
                'RowKey': '1',
                'LastUpdated': '2024-01-01'
            }
        )


if __name__ == '__main__':
    unittest.main()
