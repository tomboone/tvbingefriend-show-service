import importlib
import os
import unittest
from unittest.mock import patch

# Set a dummy connection string for test environment to avoid real DB connection
os.environ['SQLALCHEMY_CONNECTION_STRING'] = 'sqlite:///:memory:'

class TestDatabase(unittest.TestCase):

    @patch('tvbingefriend_show_service.database.create_engine')
    @patch('tvbingefriend_show_service.database.sessionmaker')
    def test_engine_creation(self, mock_sessionmaker, mock_create_engine):
        """Test that the database engine is created when get_engine is called."""
        from tvbingefriend_show_service.database import get_engine
        
        # Reset global variables
        import tvbingefriend_show_service.database as db_module
        db_module._db_engine = None
        
        get_engine()
        
        mock_create_engine.assert_called_once()

    @patch('tvbingefriend_show_service.database.get_engine')
    @patch('tvbingefriend_show_service.database.sessionmaker')
    def test_session_maker_creation(self, mock_sessionmaker, mock_get_engine):
        """Test that sessionmaker is created when get_session_maker is called."""
        from tvbingefriend_show_service.database import get_session_maker
        
        # Reset global variables
        import tvbingefriend_show_service.database as db_module
        db_module._session_maker = None
        
        get_session_maker()
        
        mock_get_engine.assert_called_once()
        mock_sessionmaker.assert_called_once()


if __name__ == '__main__':
    unittest.main()
