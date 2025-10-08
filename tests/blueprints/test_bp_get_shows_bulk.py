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

from tvbingefriend_show_service.blueprints.bp_get_shows_bulk import get_shows_bulk


class TestBpGetShowsBulk(unittest.TestCase):

    @patch('tvbingefriend_show_service.blueprints.bp_get_shows_bulk.ShowService')
    def test_get_shows_bulk_success(self, mock_show_service_class):
        """Test getting shows bulk successfully."""
        mock_service = MagicMock()
        mock_show_service_class.return_value = mock_service

        mock_shows = [
            {
                "id": 1,
                "url": "http://test1.com",
                "name": "Test Show 1",
                "type": "Scripted",
                "language": "English",
                "genres": ["Comedy"],
                "status": "Running",
                "runtime": 30,
                "averageRuntime": 30,
                "premiered": "2023-01-01",
                "ended": None,
                "officialSite": "http://official.com",
                "schedule": {"time": "20:00", "days": ["Monday"]},
                "rating": {"average": 8.5},
                "weight": 95,
                "network": {"name": "Test Network"},
                "webchannel": None,
                "dvdCountry": None,
                "externals": {"tvdb": 12345},
                "image": {"medium": "http://image.com"},
                "summary": "A test show",
                "updated": 1672531200,
                "_links": {"self": {"href": "http://api.com"}}
            },
            {
                "id": 2,
                "url": "http://test2.com",
                "name": "Test Show 2",
                "type": "Scripted",
                "language": "English",
                "genres": ["Drama"],
                "status": "Ended",
                "runtime": 60,
                "averageRuntime": 60,
                "premiered": "2022-01-01",
                "ended": "2023-01-01",
                "officialSite": None,
                "schedule": {"time": "21:00", "days": ["Tuesday"]},
                "rating": {"average": 7.5},
                "weight": 85,
                "network": None,
                "webchannel": {"name": "Test Webchannel"},
                "dvdCountry": None,
                "externals": {"tvdb": 54321},
                "image": {"medium": "http://image2.com"},
                "summary": "Another test show",
                "updated": 1672531300,
                "_links": {"self": {"href": "http://api2.com"}}
            }
        ]
        mock_service.get_shows_bulk.return_value = mock_shows

        # Create request with default params
        req = func.HttpRequest(
            method='GET',
            url='/get_shows_bulk',
            params={},
            body=None
        )

        response = get_shows_bulk(req)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'application/json')

        response_data = json.loads(response.get_body())
        self.assertEqual(len(response_data['shows']), 2)
        self.assertEqual(response_data['total'], 2)
        self.assertEqual(response_data['offset'], 0)
        self.assertEqual(response_data['limit'], 100)
        self.assertEqual(response_data['shows'][0]['name'], "Test Show 1")
        self.assertEqual(response_data['shows'][0]['url'], "http://test1.com")

        mock_service.get_shows_bulk.assert_called_once_with(0, 100)

    @patch('tvbingefriend_show_service.blueprints.bp_get_shows_bulk.ShowService')
    def test_get_shows_bulk_with_params(self, mock_show_service_class):
        """Test getting shows bulk with custom params."""
        mock_service = MagicMock()
        mock_show_service_class.return_value = mock_service

        mock_shows = [
            {
                "id": 101,
                "url": "http://test101.com",
                "name": "Test Show 101",
                "type": "Scripted",
                "language": "English",
                "genres": ["Comedy"],
                "status": "Running",
                "runtime": 30,
                "averageRuntime": 30,
                "premiered": "2023-01-01",
                "ended": None,
                "officialSite": "http://official.com",
                "schedule": {"time": "20:00", "days": ["Monday"]},
                "rating": {"average": 8.5},
                "weight": 95,
                "network": {"name": "Test Network"},
                "webchannel": None,
                "dvdCountry": None,
                "externals": {"tvdb": 12345},
                "image": {"medium": "http://image.com"},
                "summary": "A test show",
                "updated": 1672531200,
                "_links": {"self": {"href": "http://api.com"}}
            }
        ]
        mock_service.get_shows_bulk.return_value = mock_shows

        # Create request with custom params
        req = func.HttpRequest(
            method='GET',
            url='/get_shows_bulk',
            params={'offset': '100', 'limit': '50'},
            body=None
        )

        response = get_shows_bulk(req)

        self.assertEqual(response.status_code, 200)

        response_data = json.loads(response.get_body())
        self.assertEqual(response_data['offset'], 100)
        self.assertEqual(response_data['limit'], 50)

        mock_service.get_shows_bulk.assert_called_once_with(100, 50)

    @patch('tvbingefriend_show_service.blueprints.bp_get_shows_bulk.ShowService')
    def test_get_shows_bulk_limit_capped(self, mock_show_service_class):
        """Test that limit is capped at 1000."""
        mock_service = MagicMock()
        mock_show_service_class.return_value = mock_service
        mock_service.get_shows_bulk.return_value = []

        # Create request with limit > 1000
        req = func.HttpRequest(
            method='GET',
            url='/get_shows_bulk',
            params={'limit': '5000'},
            body=None
        )

        response = get_shows_bulk(req)

        self.assertEqual(response.status_code, 200)

        response_data = json.loads(response.get_body())
        self.assertEqual(response_data['limit'], 1000)  # Should be capped

        mock_service.get_shows_bulk.assert_called_once_with(0, 1000)

    @patch('tvbingefriend_show_service.blueprints.bp_get_shows_bulk.ShowService')
    def test_get_shows_bulk_empty_result(self, mock_show_service_class):
        """Test getting shows bulk with empty result."""
        mock_service = MagicMock()
        mock_show_service_class.return_value = mock_service
        mock_service.get_shows_bulk.return_value = []

        req = func.HttpRequest(
            method='GET',
            url='/get_shows_bulk',
            params={},
            body=None
        )

        response = get_shows_bulk(req)

        self.assertEqual(response.status_code, 200)

        response_data = json.loads(response.get_body())
        self.assertEqual(len(response_data['shows']), 0)
        self.assertEqual(response_data['total'], 0)


if __name__ == '__main__':
    unittest.main()