import os
import unittest
from unittest.mock import patch

# Set required env vars for module import
os.environ['DB_HOST'] = 'test_host'
os.environ['DB_NAME'] = 'test_db'
os.environ['DB_USER'] = 'test_user'

from tvbingefriend_show_service.config import _get_required_env, DB_HOST, DB_NAME, DB_USER


class TestConfig(unittest.TestCase):

    def test_db_vars_loaded(self):
        """Check if the DB connection vars are loaded correctly."""
        self.assertEqual(DB_HOST, 'test_host')
        self.assertEqual(DB_NAME, 'test_db')
        self.assertEqual(DB_USER, 'test_user')

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
