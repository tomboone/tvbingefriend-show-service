import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch
from types import ModuleType

import azure.functions as func

# Set required env vars for module import
os.environ['SQLALCHEMY_CONNECTION_STRING'] = 'sqlite:///:memory:'

# Create a mock TVMaze module to avoid import errors
mock_tvmaze_module = ModuleType('tvbingefriend_tvmaze_client')
mock_tvmaze_module.TVMazeAPI = MagicMock
sys.modules['tvbingefriend_tvmaze_client'] = mock_tvmaze_module

from tvbingefriend_show_service.blueprints.bp_get_show_summaries import get_show_summaries


class TestBpGetShowSummaries(unittest.TestCase):

    @patch('tvbingefriend_show_service.blueprints.bp_get_show_summaries.ShowService')
    def test_get_show_summaries_success(self, mock_show_service_class):
        """Test getting show summaries successfully."""
        mock_service = MagicMock()
        mock_show_service_class.return_value = mock_service

        mock_summaries = [
            {
                "id": 1,
                "name": "Test Show 1",
                "genres": ["Comedy"],
                "summary": "A test show",
                "rating": {"average": 8.5},
                "network": {"name": "Test Network"},
                "webchannel": None,
                "type": "Scripted",
                "language": "English"
            },
            {
                "id": 2,
                "name": "Test Show 2",
                "genres": ["Drama"],
                "summary": "Another test show",
                "rating": {"average": 7.5},
                "network": None,
                "webchannel": {"name": "Test Webchannel"},
                "type": "Scripted",
                "language": "English"
            }
        ]
        mock_service.get_show_summaries.return_value = mock_summaries

        # Create request with default params
        req = func.HttpRequest(
            method='GET',
            url='/get_show_summaries',
            params={},
            body=None
        )

        response = get_show_summaries(req)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'application/json')

        response_data = json.loads(response.get_body())
        self.assertEqual(len(response_data['shows']), 2)
        self.assertEqual(response_data['total'], 2)
        self.assertEqual(response_data['offset'], 0)
        self.assertEqual(response_data['limit'], 100)
        self.assertEqual(response_data['shows'][0]['name'], "Test Show 1")

        mock_service.get_show_summaries.assert_called_once_with(0, 100)

    @patch('tvbingefriend_show_service.blueprints.bp_get_show_summaries.ShowService')
    def test_get_show_summaries_with_params(self, mock_show_service_class):
        """Test getting show summaries with custom params."""
        mock_service = MagicMock()
        mock_show_service_class.return_value = mock_service

        mock_summaries = [
            {
                "id": 51,
                "name": "Test Show 51",
                "genres": ["Comedy"],
                "summary": "A test show",
                "rating": {"average": 8.5},
                "network": {"name": "Test Network"},
                "webchannel": None,
                "type": "Scripted",
                "language": "English"
            }
        ]
        mock_service.get_show_summaries.return_value = mock_summaries

        # Create request with custom params
        req = func.HttpRequest(
            method='GET',
            url='/get_show_summaries',
            params={'offset': '50', 'limit': '25'},
            body=None
        )

        response = get_show_summaries(req)

        self.assertEqual(response.status_code, 200)

        response_data = json.loads(response.get_body())
        self.assertEqual(response_data['offset'], 50)
        self.assertEqual(response_data['limit'], 25)

        mock_service.get_show_summaries.assert_called_once_with(50, 25)

    @patch('tvbingefriend_show_service.blueprints.bp_get_show_summaries.ShowService')
    def test_get_show_summaries_limit_capped(self, mock_show_service_class):
        """Test that limit is capped at 1000."""
        mock_service = MagicMock()
        mock_show_service_class.return_value = mock_service
        mock_service.get_show_summaries.return_value = []

        # Create request with limit > 1000
        req = func.HttpRequest(
            method='GET',
            url='/get_show_summaries',
            params={'limit': '2000'},
            body=None
        )

        response = get_show_summaries(req)

        self.assertEqual(response.status_code, 200)

        response_data = json.loads(response.get_body())
        self.assertEqual(response_data['limit'], 1000)  # Should be capped

        mock_service.get_show_summaries.assert_called_once_with(0, 1000)

    @patch('tvbingefriend_show_service.blueprints.bp_get_show_summaries.ShowService')
    def test_get_show_summaries_empty_result(self, mock_show_service_class):
        """Test getting show summaries with empty result."""
        mock_service = MagicMock()
        mock_show_service_class.return_value = mock_service
        mock_service.get_show_summaries.return_value = []

        req = func.HttpRequest(
            method='GET',
            url='/get_show_summaries',
            params={},
            body=None
        )

        response = get_show_summaries(req)

        self.assertEqual(response.status_code, 200)

        response_data = json.loads(response.get_body())
        self.assertEqual(len(response_data['shows']), 0)
        self.assertEqual(response_data['total'], 0)


if __name__ == '__main__':
    unittest.main()