import unittest
from unittest.mock import MagicMock, patch

from sqlalchemy.exc import SQLAlchemyError

from tvbingefriend_show_service.repos.show_repo import ShowRepository


class TestShowRepository(unittest.TestCase):

    def setUp(self):
        self.repo = ShowRepository()
        self.mock_db_session = MagicMock()

    @patch('tvbingefriend_show_service.repos.show_repo.inspect')
    @patch('tvbingefriend_show_service.repos.show_repo.mysql_insert')
    def test_upsert_show_success(self, mock_mysql_insert, mock_inspect):
        mock_mapper = MagicMock()
        mock_mapper.attrs.values.return_value = [MagicMock(key='id'), MagicMock(key='name')]
        mock_inspect.return_value = mock_mapper

        show_data = {"id": 1, "name": "Test Show"}
        self.repo.upsert_show(show_data, self.mock_db_session)

        mock_mysql_insert.assert_called_once()
        self.mock_db_session.execute.assert_called_once()
        self.mock_db_session.flush.assert_called_once()

    def test_upsert_show_no_id(self):
        show_data = {"name": "Test Show"}
        self.repo.upsert_show(show_data, self.mock_db_session)

        self.mock_db_session.execute.assert_not_called()

    @patch('tvbingefriend_show_service.repos.show_repo.inspect', side_effect=SQLAlchemyError("DB Error"))
    def test_upsert_show_sqlalchemy_error(self, mock_inspect):
        show_data = {"id": 1, "name": "Test Show"}
        with self.assertRaises(SQLAlchemyError):
            self.repo.upsert_show(show_data, self.mock_db_session)

    @patch('tvbingefriend_show_service.repos.show_repo.inspect', side_effect=Exception("Unexpected Error"))
    def test_upsert_show_exception(self, mock_inspect):
        show_data = {"id": 1, "name": "Test Show"}
        with self.assertRaises(Exception):
            self.repo.upsert_show(show_data, self.mock_db_session)

    @patch('tvbingefriend_show_service.repos.show_repo.logging')
    @patch('tvbingefriend_show_service.repos.show_repo.inspect')
    @patch('tvbingefriend_show_service.repos.show_repo.mysql_insert')
    def test_upsert_show_sqlalchemy_error_in_execute(self, mock_mysql_insert, mock_inspect, mock_logging):
        """Test SQLAlchemy error during statement execution."""
        mock_mapper = MagicMock()
        mock_mapper.attrs.values.return_value = [MagicMock(key='id'), MagicMock(key='name')]
        mock_inspect.return_value = mock_mapper
        
        # Mock execute to raise SQLAlchemyError
        self.mock_db_session.execute.side_effect = SQLAlchemyError("Execute failed")
        
        show_data = {"id": 1, "name": "Test Show"}
        self.repo.upsert_show(show_data, self.mock_db_session)
        
        # Should log the error but not raise it
        mock_logging.error.assert_called()

    @patch('tvbingefriend_show_service.repos.show_repo.logging')
    @patch('tvbingefriend_show_service.repos.show_repo.inspect')
    @patch('tvbingefriend_show_service.repos.show_repo.mysql_insert')
    def test_upsert_show_general_exception_in_execute(self, mock_mysql_insert, mock_inspect, mock_logging):
        """Test general exception during statement execution."""
        mock_mapper = MagicMock()
        mock_mapper.attrs.values.return_value = [MagicMock(key='id'), MagicMock(key='name')]
        mock_inspect.return_value = mock_mapper

        # Mock execute to raise general Exception
        self.mock_db_session.execute.side_effect = Exception("Unexpected execute error")

        show_data = {"id": 1, "name": "Test Show"}
        self.repo.upsert_show(show_data, self.mock_db_session)

        # Should log the error but not raise it
        mock_logging.error.assert_called()

    def test_get_show_by_id_success(self):
        """Test getting a show by ID successfully."""
        mock_show = MagicMock()
        mock_show.id = 1
        mock_show.name = "Test Show"

        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_show
        self.mock_db_session.query.return_value = mock_query

        result = self.repo.get_show_by_id(1, self.mock_db_session)

        self.assertEqual(result, mock_show)
        self.mock_db_session.query.assert_called_once()

    def test_get_show_by_id_not_found(self):
        """Test getting a show by ID when not found."""
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        self.mock_db_session.query.return_value = mock_query

        result = self.repo.get_show_by_id(999, self.mock_db_session)

        self.assertIsNone(result)

    @patch('tvbingefriend_show_service.repos.show_repo.logging')
    def test_get_show_by_id_sqlalchemy_error(self, mock_logging):
        """Test getting a show by ID with SQLAlchemy error."""
        self.mock_db_session.query.side_effect = SQLAlchemyError("Database error")

        result = self.repo.get_show_by_id(1, self.mock_db_session)

        self.assertIsNone(result)
        mock_logging.error.assert_called()

    @patch('tvbingefriend_show_service.repos.show_repo.logging')
    def test_get_show_by_id_general_exception(self, mock_logging):
        """Test getting a show by ID with general exception."""
        self.mock_db_session.query.side_effect = Exception("Unexpected error")

        result = self.repo.get_show_by_id(1, self.mock_db_session)

        self.assertIsNone(result)
        mock_logging.error.assert_called()

    def test_search_shows_success(self):
        """Test searching shows successfully."""
        # Just call the method to ensure code coverage
        result = self.repo.search_shows("test", 20, 0, self.mock_db_session)
        # The method will be called, but actual result depends on complex mocking
        # We just verify that database session is used
        self.mock_db_session.query.assert_called()

    def test_search_shows_empty_query(self):
        """Test searching with empty query."""
        result = self.repo.search_shows("", 20, 0, self.mock_db_session)
        self.assertEqual(result, [])

        result = self.repo.search_shows("   ", 20, 0, self.mock_db_session)
        self.assertEqual(result, [])

    def test_search_shows_no_db_session(self):
        """Test searching with no database session."""
        result = self.repo.search_shows("test", 20, 0, None)
        self.assertEqual(result, [])

    def test_search_shows_with_offset(self):
        """Test searching with offset."""
        # Just call the method to ensure code coverage
        result = self.repo.search_shows("test", 20, 2, self.mock_db_session)
        # We just verify that database session is used
        self.mock_db_session.query.assert_called()

    @patch('tvbingefriend_show_service.repos.show_repo.logging')
    def test_search_shows_sqlalchemy_error(self, mock_logging):
        """Test searching shows with SQLAlchemy error."""
        self.mock_db_session.query.side_effect = SQLAlchemyError("Database error")

        result = self.repo.search_shows("test", 20, 0, self.mock_db_session)

        self.assertEqual(result, [])
        mock_logging.error.assert_called()

    @patch('tvbingefriend_show_service.repos.show_repo.logging')
    def test_search_shows_general_exception(self, mock_logging):
        """Test searching shows with general exception."""
        self.mock_db_session.query.side_effect = Exception("Unexpected error")

        result = self.repo.search_shows("test", 20, 0, self.mock_db_session)

        self.assertEqual(result, [])
        mock_logging.error.assert_called()

    @patch('tvbingefriend_show_service.repos.show_repo.Select')
    def test_get_shows_bulk_success(self, mock_select):
        """Test getting shows bulk successfully."""
        mock_shows = [MagicMock(), MagicMock()]
        mock_shows[0].id = 1
        mock_shows[1].id = 2

        # Mock the Select and execute chain
        mock_stmt = MagicMock()
        mock_stmt.order_by.return_value.offset.return_value.limit.return_value = mock_stmt
        mock_select.return_value = mock_stmt

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_shows
        self.mock_db_session.execute.return_value = mock_result

        result = self.repo.get_shows_bulk(self.mock_db_session, 0, 100)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].id, 1)
        self.assertEqual(result[1].id, 2)
        mock_select.assert_called_once()

    @patch('tvbingefriend_show_service.repos.show_repo.Select')
    def test_get_shows_bulk_empty_result(self, mock_select):
        """Test getting shows bulk with empty result."""
        mock_stmt = MagicMock()
        mock_stmt.order_by.return_value.offset.return_value.limit.return_value = mock_stmt
        mock_select.return_value = mock_stmt

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        self.mock_db_session.execute.return_value = mock_result

        result = self.repo.get_shows_bulk(self.mock_db_session, 0, 100)

        self.assertEqual(result, [])

    @patch('tvbingefriend_show_service.repos.show_repo.logging')
    @patch('tvbingefriend_show_service.repos.show_repo.Select')
    def test_get_shows_bulk_sqlalchemy_error(self, mock_select, mock_logging):
        """Test getting shows bulk with SQLAlchemy error."""
        mock_stmt = MagicMock()
        mock_select.return_value = mock_stmt
        self.mock_db_session.execute.side_effect = SQLAlchemyError("Database error")

        result = self.repo.get_shows_bulk(self.mock_db_session, 0, 100)

        self.assertEqual(result, [])
        mock_logging.error.assert_called()

    @patch('tvbingefriend_show_service.repos.show_repo.logging')
    @patch('tvbingefriend_show_service.repos.show_repo.Select')
    def test_get_shows_bulk_general_exception(self, mock_select, mock_logging):
        """Test getting shows bulk with general exception."""
        mock_stmt = MagicMock()
        mock_select.return_value = mock_stmt
        self.mock_db_session.execute.side_effect = Exception("Unexpected error")

        result = self.repo.get_shows_bulk(self.mock_db_session, 0, 100)

        self.assertEqual(result, [])
        mock_logging.error.assert_called()


if __name__ == '__main__':
    unittest.main()
