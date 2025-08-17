import os
import unittest
from unittest.mock import patch

# Set required env vars for module import
os.environ['DB_HOST'] = 'test_host'
os.environ['DB_NAME'] = 'test_db'
os.environ['DB_USER'] = 'test_user'

# This needs to be imported after the environment is patched
from tvbingefriend_show_service.config import _get_setting, DB_HOST, DB_NAME, DB_USER


class TestConfig(unittest.TestCase):

    def test_db_vars_loaded_from_env(self):
        """Check if the DB connection vars are loaded correctly from the environment."""
        self.assertEqual(DB_HOST, 'test_host')
        self.assertEqual(DB_NAME, 'test_db')
        self.assertEqual(DB_USER, 'test_user')

    @patch.dict(os.environ, {'TEST_VAR': 'test_value'})
    def test_get_setting_found_in_env(self):
        """Test _get_setting when a variable is present in the environment."""
        self.assertEqual(_get_setting('TEST_VAR'), 'test_value')

    @patch('tvbingefriend_show_service.config._local_settings', {'TEST_VAR': 'local_value'})
    def test_get_setting_fallback_to_local_settings(self):
        """Test _get_setting falls back to local settings when env var is missing."""
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(_get_setting('TEST_VAR'), 'local_value')

    def test_get_setting_missing_required(self):
        """Test _get_setting raises ValueError when a required variable is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "Missing required setting: 'MISSING_VAR'"):
                _get_setting('MISSING_VAR', required=True)

    def test_get_setting_missing_not_required(self):
        """Test _get_setting returns None when a non-required variable is missing."""
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(_get_setting('MISSING_VAR', required=False))

    def test_get_setting_missing_not_required_with_default(self):
        """Test _get_setting returns the default value for a missing non-required variable."""
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(_get_setting('MISSING_VAR', required=False, default='default_val'), 'default_val')


if __name__ == '__main__':
    unittest.main()
