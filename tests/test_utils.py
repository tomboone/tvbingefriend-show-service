import os
import unittest
from unittest.mock import patch, MagicMock

# Set required env var for module import to use the test database
os.environ['SQLALCHEMY_CONNECTION_STRING'] = 'sqlite:///:memory:'

from tvbingefriend_show_service.utils import db_session_manager


class TestUtils(unittest.TestCase):

    @patch('tvbingefriend_show_service.utils.get_session_maker')
    def test_db_session_manager_success(self, mock_get_session_maker):
        mock_session = MagicMock()
        mock_session_maker = MagicMock()
        mock_session_maker.return_value = mock_session
        mock_get_session_maker.return_value = mock_session_maker

        with db_session_manager() as session:
            self.assertEqual(session, mock_session)

        mock_get_session_maker.assert_called_once()
        mock_session_maker.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.rollback.assert_not_called()
        mock_session.close.assert_called_once()

    @patch('tvbingefriend_show_service.utils.get_session_maker')
    def test_db_session_manager_exception(self, mock_get_session_maker):
        mock_session = MagicMock()
        mock_session_maker = MagicMock()
        mock_session_maker.return_value = mock_session
        mock_get_session_maker.return_value = mock_session_maker

        with self.assertRaises(Exception):
            with db_session_manager():
                raise Exception("Test Exception")

        mock_get_session_maker.assert_called_once()
        mock_session_maker.assert_called_once()
        mock_session.commit.assert_not_called()
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
