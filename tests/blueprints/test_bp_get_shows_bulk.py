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

        mock_service.get_shows_bulk.assert_called_once_with(0, 100, None)

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

        mock_service.get_shows_bulk.assert_called_once_with(100, 50, None)

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

        mock_service.get_shows_bulk.assert_called_once_with(0, 1000, None)

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

    @patch('tvbingefriend_show_service.blueprints.bp_get_shows_bulk.ShowService')
    def test_get_shows_bulk_with_show_ids(self, mock_show_service_class):
        """Test getting shows bulk with specific show IDs."""
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
                "id": 5,
                "url": "http://test5.com",
                "name": "Test Show 5",
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
                "image": {"medium": "http://image5.com"},
                "summary": "Another test show",
                "updated": 1672531300,
                "_links": {"self": {"href": "http://api5.com"}}
            }
        ]
        mock_service.get_shows_bulk.return_value = mock_shows

        # Create request with show_ids parameter
        req = func.HttpRequest(
            method='GET',
            url='/get_shows_bulk',
            params={'show_ids': '1,5,10'},
            body=None
        )

        response = get_shows_bulk(req)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'application/json')

        response_data = json.loads(response.get_body())
        self.assertEqual(len(response_data['shows']), 2)
        self.assertEqual(response_data['total'], 2)
        self.assertEqual(response_data['show_ids'], [1, 5, 10])
        self.assertEqual(response_data['shows'][0]['id'], 1)
        self.assertEqual(response_data['shows'][1]['id'], 5)

        # Verify service was called with show_ids
        mock_service.get_shows_bulk.assert_called_once_with(0, 100, [1, 5, 10])

    @patch('tvbingefriend_show_service.blueprints.bp_get_shows_bulk.ShowService')
    def test_get_shows_bulk_with_show_ids_and_limit(self, mock_show_service_class):
        """Test getting shows bulk with specific show IDs and custom limit."""
        mock_service = MagicMock()
        mock_show_service_class.return_value = mock_service

        mock_shows = [
            {
                "id": 100,
                "url": "http://test100.com",
                "name": "Test Show 100",
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

        # Create request with show_ids and custom limit
        req = func.HttpRequest(
            method='GET',
            url='/get_shows_bulk',
            params={'show_ids': '100,200,300', 'limit': '50'},
            body=None
        )

        response = get_shows_bulk(req)

        self.assertEqual(response.status_code, 200)

        response_data = json.loads(response.get_body())
        self.assertEqual(response_data['limit'], 50)
        self.assertEqual(response_data['show_ids'], [100, 200, 300])

        # Verify service was called with correct params (offset should be ignored when show_ids provided)
        mock_service.get_shows_bulk.assert_called_once_with(0, 50, [100, 200, 300])

    @patch('tvbingefriend_show_service.blueprints.bp_get_shows_bulk.ShowService')
    def test_get_shows_bulk_invalid_show_ids_format(self, mock_show_service_class):
        """Test getting shows bulk with invalid show_ids format."""
        mock_service = MagicMock()
        mock_show_service_class.return_value = mock_service

        # Create request with invalid show_ids (non-numeric)
        req = func.HttpRequest(
            method='GET',
            url='/get_shows_bulk',
            params={'show_ids': '1,abc,3'},
            body=None
        )

        response = get_shows_bulk(req)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.mimetype, 'application/json')

        response_data = json.loads(response.get_body())
        self.assertIn('error', response_data)
        self.assertIn('Invalid show_ids format', response_data['error'])

        # Verify service was NOT called
        mock_service.get_shows_bulk.assert_not_called()

    @patch('tvbingefriend_show_service.blueprints.bp_get_shows_bulk.ShowService')
    def test_get_shows_bulk_with_show_ids_with_spaces(self, mock_show_service_class):
        """Test getting shows bulk with show IDs containing spaces."""
        mock_service = MagicMock()
        mock_show_service_class.return_value = mock_service
        mock_service.get_shows_bulk.return_value = []

        # Create request with show_ids that have spaces
        req = func.HttpRequest(
            method='GET',
            url='/get_shows_bulk',
            params={'show_ids': ' 1 , 2 , 3 '},
            body=None
        )

        response = get_shows_bulk(req)

        self.assertEqual(response.status_code, 200)

        response_data = json.loads(response.get_body())
        self.assertEqual(response_data['show_ids'], [1, 2, 3])

        # Verify service was called with trimmed IDs
        mock_service.get_shows_bulk.assert_called_once_with(0, 100, [1, 2, 3])

    @patch('tvbingefriend_show_service.blueprints.bp_get_shows_bulk.ShowService')
    def test_get_shows_bulk_with_empty_show_ids(self, mock_show_service_class):
        """Test getting shows bulk with empty show_ids parameter."""
        mock_service = MagicMock()
        mock_show_service_class.return_value = mock_service
        mock_service.get_shows_bulk.return_value = []

        # Create request with empty show_ids
        req = func.HttpRequest(
            method='GET',
            url='/get_shows_bulk',
            params={'show_ids': ''},
            body=None
        )

        response = get_shows_bulk(req)

        self.assertEqual(response.status_code, 200)

        # Empty show_ids should be treated as None (fall back to offset-based pagination)
        mock_service.get_shows_bulk.assert_called_once_with(0, 100, None)


if __name__ == '__main__':
    unittest.main()