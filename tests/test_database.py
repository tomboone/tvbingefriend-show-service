import importlib
import os
import unittest
from unittest.mock import patch

# Set a dummy connection string for test environment to avoid real DB connection
os.environ['SQLALCHEMY_CONNECTION_STRING'] = 'sqlite:///:memory:'

class TestDatabase(unittest.TestCase):

    # Patch the functions at their source, so that when the database module
    # is reloaded, it uses our mocks.
    @patch('sqlalchemy.create_engine')
    @patch('sqlalchemy.orm.sessionmaker')
    def test_engine_and_session_creation(self, mock_sessionmaker, mock_create_engine):
        """Test that the database engine and sessionmaker are created on module load."""
        from tvbingefriend_show_service import database
        importlib.reload(database)

        mock_create_engine.assert_called_once()
        mock_sessionmaker.assert_called_once()


if __name__ == '__main__':
    unittest.main()
