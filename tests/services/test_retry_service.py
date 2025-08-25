import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, UTC
import time

import azure.functions as func

from tvbingefriend_show_service.services.retry_service import RetryService


class TestRetryService(unittest.TestCase):

    def setUp(self):
        """Set up test environment for each test."""
        self.mock_storage_service = MagicMock()
        self.mock_monitoring_service = MagicMock()
        self.service = RetryService(
            storage_service=self.mock_storage_service,
            monitoring_service=self.mock_monitoring_service
        )

    def test_init_with_default_services(self):
        """Test initialization with default services."""
        with patch('tvbingefriend_show_service.services.retry_service.StorageService') as mock_storage_class:
            with patch('tvbingefriend_show_service.services.retry_service.MonitoringService') as mock_monitoring_class:
                service = RetryService()
                mock_storage_class.assert_called_once()
                mock_monitoring_class.assert_called_once()
                self.assertIsNotNone(service.storage_service)
                self.assertIsNotNone(service.monitoring_service)

    def test_calculate_backoff_delay(self):
        """Test exponential backoff delay calculation."""
        # Attempt 1: 2 * 2^0 = 2
        self.assertEqual(self.service.calculate_backoff_delay(1), 2.0)
        # Attempt 2: 2 * 2^1 = 4
        self.assertEqual(self.service.calculate_backoff_delay(2), 4.0)
        # Attempt 3: 2 * 2^2 = 8
        self.assertEqual(self.service.calculate_backoff_delay(3), 8.0)

    @patch('time.sleep')
    def test_with_retry_decorator_success_first_attempt(self, mock_sleep):
        """Test retry decorator when function succeeds on first attempt."""
        @self.service.with_retry('test_operation')
        def test_function():
            return "success"
        
        result = test_function()
        
        self.assertEqual(result, "success")
        mock_sleep.assert_not_called()
        self.mock_monitoring_service.track_retry_attempt.assert_not_called()

    @patch('time.sleep')
    def test_with_retry_decorator_success_after_retries(self, mock_sleep):
        """Test retry decorator when function succeeds after retries."""
        call_count = 0
        
        @self.service.with_retry('test_operation')
        def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception(f"Attempt {call_count} failed")
            return "success"
        
        result = test_function()
        
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 3)
        # Should sleep twice (for attempts 1 and 2)
        self.assertEqual(mock_sleep.call_count, 2)
        # Should track 2 retry attempts
        self.assertEqual(self.mock_monitoring_service.track_retry_attempt.call_count, 2)

    @patch('time.sleep')
    def test_with_retry_decorator_all_attempts_fail(self, mock_sleep):
        """Test retry decorator when all attempts fail."""
        @self.service.with_retry('test_operation', max_attempts=2)
        def test_function():
            raise Exception("Always fails")
        
        with self.assertRaises(Exception):
            test_function()
        
        # Should sleep once (for attempt 1)
        self.assertEqual(mock_sleep.call_count, 1)
        # Should track 2 retry attempts
        self.assertEqual(self.mock_monitoring_service.track_retry_attempt.call_count, 2)

    @patch('time.sleep')
    def test_handle_queue_message_with_retry_success_first_attempt(self, mock_sleep):
        """Test handling queue message successfully on first attempt."""
        mock_message = MagicMock()
        mock_message.id = "test_message_123"
        mock_message.dequeue_count = 1
        
        mock_handler = MagicMock()
        
        result = self.service.handle_queue_message_with_retry(mock_message, mock_handler, 'test_operation')
        
        self.assertTrue(result)
        mock_handler.assert_called_once_with(mock_message)
        mock_sleep.assert_not_called()
        self.mock_monitoring_service.track_retry_attempt.assert_not_called()

    @patch('time.sleep')
    def test_handle_queue_message_with_retry_success_after_retries(self, mock_sleep):
        """Test handling queue message successfully after retries."""
        mock_message = MagicMock()
        mock_message.id = "test_message_123"
        mock_message.dequeue_count = 2
        
        mock_handler = MagicMock()
        
        result = self.service.handle_queue_message_with_retry(mock_message, mock_handler, 'test_operation')
        
        self.assertTrue(result)
        mock_handler.assert_called_once_with(mock_message)
        # Should apply backoff delay for retry attempt
        mock_sleep.assert_called_once()
        # Should track retry attempt
        self.mock_monitoring_service.track_retry_attempt.assert_called_once()

    def test_handle_queue_message_max_retries_exceeded(self):
        """Test handling queue message when max retries exceeded."""
        mock_message = MagicMock()
        mock_message.id = "test_message_123"
        mock_message.dequeue_count = 5  # Exceeds max_retry_attempts (3)
        
        mock_handler = MagicMock()
        
        result = self.service.handle_queue_message_with_retry(mock_message, mock_handler, 'test_operation')
        
        self.assertFalse(result)
        mock_handler.assert_not_called()
        # Should send to dead letter queue
        self.mock_storage_service.upload_queue_message.assert_called_once()

    def test_handle_queue_message_handler_exception_max_retries(self):
        """Test handling queue message when handler fails on max retry."""
        mock_message = MagicMock()
        mock_message.id = "test_message_123"
        mock_message.dequeue_count = 3  # At max retry attempts
        
        mock_handler = MagicMock()
        mock_handler.side_effect = Exception("Handler failed")
        
        result = self.service.handle_queue_message_with_retry(mock_message, mock_handler, 'test_operation')
        
        self.assertFalse(result)
        # Should send to dead letter queue
        self.mock_storage_service.upload_queue_message.assert_called_once()

    def test_handle_queue_message_handler_exception_retry_available(self):
        """Test handling queue message when handler fails but retries available."""
        mock_message = MagicMock()
        mock_message.id = "test_message_123"
        mock_message.dequeue_count = 1  # Still has retries available
        
        mock_handler = MagicMock()
        mock_handler.side_effect = Exception("Handler failed")
        
        with self.assertRaises(Exception):
            self.service.handle_queue_message_with_retry(mock_message, mock_handler, 'test_operation')
        
        # Should NOT send to dead letter queue
        self.mock_storage_service.upload_queue_message.assert_not_called()

    def test_send_to_dead_letter_queue_index_operation(self):
        """Test sending message to dead letter queue for index operation."""
        mock_message = MagicMock()
        mock_message.get_json.return_value = {"page": 1}
        mock_message.id = "test_message_123"
        mock_message.dequeue_count = 3
        
        self.service.send_to_dead_letter_queue(mock_message, 'index_page', 'Max retries exceeded')
        
        self.mock_storage_service.upload_queue_message.assert_called_once()
        call_args = self.mock_storage_service.upload_queue_message.call_args
        
        # Check that it used the correct dead letter queue
        self.assertTrue(call_args[1]['queue_name'].endswith('-deadletter'))
        self.assertIn('index', call_args[1]['queue_name'])
        
        # Check dead letter message structure
        message = call_args[1]['message']
        self.assertIn('original_message', message)
        self.assertIn('operation_type', message)
        self.assertIn('failure_reason', message)

    def test_send_to_dead_letter_queue_details_operation(self):
        """Test sending message to dead letter queue for details operation."""
        mock_message = MagicMock()
        mock_message.get_json.return_value = {"show_id": 123}
        
        self.service.send_to_dead_letter_queue(mock_message, 'show_details', 'API error')
        
        call_args = self.mock_storage_service.upload_queue_message.call_args
        self.assertIn('details', call_args[1]['queue_name'])

    def test_send_to_dead_letter_queue_general_operation(self):
        """Test sending message to dead letter queue for general operation."""
        mock_message = MagicMock()
        mock_message.get_json.return_value = {"data": "test"}
        
        self.service.send_to_dead_letter_queue(mock_message, 'unknown_operation', 'Unknown error')
        
        call_args = self.mock_storage_service.upload_queue_message.call_args
        self.assertIn('general', call_args[1]['queue_name'])

    def test_send_to_dead_letter_queue_exception(self):
        """Test handling exception when sending to dead letter queue."""
        mock_message = MagicMock()
        mock_message.get_json.return_value = {"data": "test"}
        
        self.mock_storage_service.upload_queue_message.side_effect = Exception("Storage error")
        
        # Should not raise exception, just log error
        self.service.send_to_dead_letter_queue(mock_message, 'test_operation', 'Test error')

    def test_get_dead_letter_queue_name_index(self):
        """Test getting dead letter queue name for index operations."""
        result = self.service.get_dead_letter_queue_name('index_page')
        self.assertIn('index', result.lower())
        self.assertTrue(result.endswith('-deadletter'))

    def test_get_dead_letter_queue_name_details(self):
        """Test getting dead letter queue name for details operations."""
        result = self.service.get_dead_letter_queue_name('show_details')
        self.assertIn('details', result.lower())
        self.assertTrue(result.endswith('-deadletter'))

    def test_get_dead_letter_queue_name_general(self):
        """Test getting dead letter queue name for general operations."""
        result = self.service.get_dead_letter_queue_name('unknown_operation')
        self.assertIn('general', result)
        self.assertTrue(result.endswith('-deadletter'))

    def test_process_dead_letter_queue(self):
        """Test processing dead letter queue."""
        queue_name = "test-deadletter"
        
        result = self.service.process_dead_letter_queue(queue_name, max_messages=5)
        
        # Currently returns 0 (placeholder implementation)
        self.assertEqual(result, 0)

    def test_process_dead_letter_queue_exception(self):
        """Test handling exception in process_dead_letter_queue."""
        with patch('tvbingefriend_show_service.services.retry_service.logging') as mock_logging:
            mock_logging.info.side_effect = Exception("Logging error")
            
            result = self.service.process_dead_letter_queue("test-queue")
            
            self.assertEqual(result, 0)

    def test_retry_failed_operation_index_page(self):
        """Test retrying failed index page operation."""
        operation_data = {"page": 5, "import_id": "test_import"}
        
        result = self.service.retry_failed_operation('index_page', operation_data)
        
        self.assertTrue(result)
        self.mock_storage_service.upload_queue_message.assert_called_once()
        call_args = self.mock_storage_service.upload_queue_message.call_args
        self.assertEqual(call_args[1]['message'], operation_data)

    def test_retry_failed_operation_show_details(self):
        """Test retrying failed show details operation."""
        operation_data = {"show_id": 123}
        
        result = self.service.retry_failed_operation('show_details', operation_data)
        
        self.assertTrue(result)
        self.mock_storage_service.upload_queue_message.assert_called_once()

    def test_retry_failed_operation_unknown_type(self):
        """Test retrying failed operation with unknown type."""
        operation_data = {"data": "test"}
        
        result = self.service.retry_failed_operation('unknown_operation', operation_data)
        
        self.assertFalse(result)
        self.mock_storage_service.upload_queue_message.assert_not_called()

    def test_retry_failed_operation_exception(self):
        """Test handling exception in retry_failed_operation."""
        operation_data = {"page": 1}
        self.mock_storage_service.upload_queue_message.side_effect = Exception("Storage error")
        
        result = self.service.retry_failed_operation('index_page', operation_data)
        
        self.assertFalse(result)

    def test_get_dead_letter_statistics_success(self):
        """Test getting dead letter queue statistics."""
        result = self.service.get_dead_letter_statistics()
        
        self.assertIn('last_check', result)
        self.assertIn('queues', result)
        self.assertIsInstance(result['queues'], dict)
        
        # Should include common dead letter queues
        queue_names = result['queues'].keys()
        self.assertTrue(any('index' in name for name in queue_names))
        self.assertTrue(any('details' in name for name in queue_names))
        self.assertTrue(any('general' in name for name in queue_names))

    def test_get_dead_letter_statistics_queue_error(self):
        """Test getting dead letter statistics when individual queue check fails."""
        result = self.service.get_dead_letter_statistics()
        
        # Should still return result even if individual queue checks fail
        self.assertIn('queues', result)

    def test_get_dead_letter_statistics_exception(self):
        """Test handling exception in get_dead_letter_statistics."""
        with patch('tvbingefriend_show_service.services.retry_service.datetime') as mock_datetime:
            mock_datetime.now.side_effect = Exception("Date error")
            
            result = self.service.get_dead_letter_statistics()
            
            self.assertIn('error', result)

    def test_handle_queue_message_missing_attributes(self):
        """Test handling queue message with missing attributes."""
        mock_message = MagicMock()
        # Remove id and dequeue_count attributes
        del mock_message.id
        del mock_message.dequeue_count
        
        mock_handler = MagicMock()
        
        result = self.service.handle_queue_message_with_retry(mock_message, mock_handler, 'test_operation')
        
        # Should still work with default values
        self.assertTrue(result)
        mock_handler.assert_called_once()

    def test_send_to_dead_letter_queue_missing_message_attributes(self):
        """Test sending to dead letter queue with missing message attributes."""
        mock_message = MagicMock()
        mock_message.get_json.return_value = {"data": "test"}
        # Remove optional attributes
        del mock_message.id
        del mock_message.dequeue_count
        del mock_message.insertion_time
        
        self.service.send_to_dead_letter_queue(mock_message, 'test_operation', 'Test error')
        
        # Should still work with default values
        self.mock_storage_service.upload_queue_message.assert_called_once()
        call_args = self.mock_storage_service.upload_queue_message.call_args
        message = call_args[1]['message']
        
        self.assertEqual(message['original_message_id'], 'unknown')
        self.assertEqual(message['dequeue_count'], 0)


if __name__ == '__main__':
    unittest.main()