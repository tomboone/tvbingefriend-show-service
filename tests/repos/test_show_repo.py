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


if __name__ == '__main__':
    unittest.main()
