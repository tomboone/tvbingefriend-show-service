import os
import unittest
from unittest.mock import patch

# Set required env var for module import
os.environ['SQLALCHEMY_CONNECTION_STRING'] = 'sqlite:///:memory:'

from tvbingefriend_show_service.config import _get_required_env, SQLALCHEMY_CONNECTION_STRING


class TestConfig(unittest.TestCase):

    def test_sqlalchemy_connection_string_loaded(self):
        """Check if the connection string is loaded correctly."""
        self.assertEqual(SQLALCHEMY_CONNECTION_STRING, 'sqlite:///:memory:')

    @patch.dict(os.environ, {'TEST_VAR': 'test_value'})
    def test_get_required_env_found(self):
        """Test _get_required_env when variable is present."""
        self.assertEqual(_get_required_env('TEST_VAR'), 'test_value')

    def test_get_required_env_missing(self):
        """Test _get_required_env when variable is missing."""
        # Ensure the variable is not in the environment for this test
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "Missing required environment variable: 'MISSING_VAR'"):
                _get_required_env('MISSING_VAR')


if __name__ == '__main__':
    unittest.main()
