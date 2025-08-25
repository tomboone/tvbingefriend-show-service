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

    def test_missing_connection_string(self):
        """Test error when SQLALCHEMY_CONNECTION_STRING is missing."""
        # Reset global variables
        import tvbingefriend_show_service.database as db_module
        db_module._db_engine = None
        
        # Temporarily unset the connection string
        original_connection_string = os.environ.get('SQLALCHEMY_CONNECTION_STRING')
        if 'SQLALCHEMY_CONNECTION_STRING' in os.environ:
            del os.environ['SQLALCHEMY_CONNECTION_STRING']
        
        try:
            with patch('tvbingefriend_show_service.database.SQLALCHEMY_CONNECTION_STRING', None):
                from tvbingefriend_show_service.database import get_engine
                with self.assertRaises(ValueError):
                    get_engine()
        finally:
            # Restore the connection string
            if original_connection_string:
                os.environ['SQLALCHEMY_CONNECTION_STRING'] = original_connection_string

    @patch('tvbingefriend_show_service.database.create_engine')
    @patch('tvbingefriend_show_service.database.tempfile.NamedTemporaryFile')
    def test_ssl_certificate_processing(self, mock_tempfile, mock_create_engine):
        """Test SSL certificate processing with CA content."""
        # Reset global variables
        import tvbingefriend_show_service.database as db_module
        db_module._db_engine = None
        db_module._cert_file_path = None
        
        # Mock CA content with multiple certificates
        mock_ca_content = """-----BEGIN CERTIFICATE-----
MIIDjjCCAnagAwIBAgIQAzrx5qcRqaC7KGSxHQn65TANBgkqhkiG9w0BAQsFADA9
MQswCQYDVQQGEwJVUzEPMA0GA1UEChMGQW1hem9uMRwwGgYDVQQDExNBbWF6b24g
UlNBIDIwNDggTTAeFw0yMjA4MjMxNzI5MDhaFw0zMDA4MjMxNzI5MDhaMD0xCzAJ
BgNVBAYTAlVTMQ8wDQYDVQQKEwZBbWF6b24xHDAaBgNVBAMTE0FtYXpvbiBSU0Eg
MjA0OCBNMDCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAN2d3+K4N=
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
MIIFQTCCAymgAwIBAgITBmyf1XSXNmY/Owua2eiedgPySjANBgkqhkiG9w0BAQsF
ADA5MQswCQYDVQQGEwJVUzEPMA0GA1UEChMGQW1hem9uMRwwGgYDVQQDExNBbWF6
b24gUlNBIDIwNDggTTEwHhcNMjIwODIzMTcyOTA4WhcNMzAwODIzMTcyOTA4WjBH
MQswCQYDVQQGEwJVUzEPMA0GA1UEChMGQW1hem9uMRwwGgYDVQQDExNBbWF6b24g
UlNBIDIwNDggTTEwggIiMA0GCSqGSIb3DQEBAQUAA4ICDwAwggIKAoICAQCkJ2l=
-----END CERTIFICATE-----"""
        
        # Mock the tempfile
        mock_cert_file = mock_tempfile.return_value.__enter__.return_value
        mock_cert_file.name = '/tmp/test_cert.pem'
        
        with patch('tvbingefriend_show_service.database.MYSQL_SSL_CA_CONTENT', mock_ca_content):
            from tvbingefriend_show_service.database import get_engine
            get_engine()
        
        # Verify certificate file was written with first certificate only
        mock_cert_file.write.assert_called_once()
        written_content = mock_cert_file.write.call_args[0][0]
        self.assertIn('-----BEGIN CERTIFICATE-----', written_content)
        self.assertIn('-----END CERTIFICATE-----', written_content)
        
        # Verify create_engine was called with SSL args
        mock_create_engine.assert_called_once()
        call_args = mock_create_engine.call_args
        self.assertIn('connect_args', call_args[1])
        connect_args = call_args[1]['connect_args']
        self.assertEqual(connect_args['ssl_ca'], '/tmp/test_cert.pem')
        self.assertFalse(connect_args['ssl_disabled'])

    @patch('tvbingefriend_show_service.database.create_engine')
    def test_ssl_certificate_processing_no_certificates(self, mock_create_engine):
        """Test SSL processing when no valid certificates are found."""
        # Reset global variables
        import tvbingefriend_show_service.database as db_module
        db_module._db_engine = None
        db_module._cert_file_path = None
        
        # Mock CA content without valid certificates
        mock_ca_content = "No valid certificates here"
        
        with patch('tvbingefriend_show_service.database.MYSQL_SSL_CA_CONTENT', mock_ca_content):
            from tvbingefriend_show_service.database import get_engine
            get_engine()
        
        # Should still create engine but without SSL connect_args
        mock_create_engine.assert_called_once()
        call_args = mock_create_engine.call_args
        connect_args = call_args[1].get('connect_args', {})
        self.assertNotIn('ssl_ca', connect_args)

    def test_session_maker_backward_compatibility(self):
        """Test SessionMaker function for backward compatibility."""
        with patch('tvbingefriend_show_service.database.get_session_maker') as mock_get_session_maker:
            mock_session_maker = mock_get_session_maker.return_value
            mock_session = mock_session_maker.return_value
            
            from tvbingefriend_show_service.database import SessionMaker
            result = SessionMaker()
            
            mock_get_session_maker.assert_called_once()
            mock_session_maker.assert_called_once()
            self.assertEqual(result, mock_session)


if __name__ == '__main__':
    unittest.main()
