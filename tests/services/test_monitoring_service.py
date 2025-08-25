import unittest
from unittest.mock import MagicMock, patch

from tvbingefriend_show_service.services.monitoring_service import MonitoringService, ImportStatus


class TestMonitoringService(unittest.TestCase):

    def setUp(self):
        """Set up test environment for each test."""
        self.mock_storage_service = MagicMock()
        self.service = MonitoringService(storage_service=self.mock_storage_service)

    def test_init_with_default_storage_service(self):
        """Test initialization with default storage service."""
        with patch('tvbingefriend_show_service.services.monitoring_service.StorageService') as mock_storage_class:
            service = MonitoringService()
            mock_storage_class.assert_called_once()
            self.assertIsNotNone(service.storage_service)

    def test_start_bulk_import_tracking(self):
        """Test starting bulk import tracking."""
        import_id = "test_import_123"
        start_page = 1
        estimated_pages = 100
        
        self.service.start_bulk_import_tracking(import_id, start_page, estimated_pages)
        
        self.mock_storage_service.upsert_entity.assert_called_once()
        call_args = self.mock_storage_service.upsert_entity.call_args
        entity = call_args[1]['entity']
        
        self.assertEqual(entity['PartitionKey'], 'bulk_import')
        self.assertEqual(entity['RowKey'], import_id)
        self.assertEqual(entity['Status'], ImportStatus.IN_PROGRESS.value)
        self.assertEqual(entity['StartPage'], start_page)
        self.assertEqual(entity['EstimatedPages'], estimated_pages)

    def test_start_bulk_import_tracking_no_estimated_pages(self):
        """Test starting bulk import tracking without estimated pages."""
        import_id = "test_import_123"
        
        self.service.start_bulk_import_tracking(import_id)
        
        call_args = self.mock_storage_service.upsert_entity.call_args
        entity = call_args[1]['entity']
        self.assertEqual(entity['EstimatedPages'], -1)

    def test_update_import_progress_success(self):
        """Test updating import progress successfully."""
        import_id = "test_import_123"
        completed_page = 5
        
        # Mock existing entity
        existing_entity = {
            'PartitionKey': 'bulk_import',
            'RowKey': import_id,
            'CompletedPages': 3,
            'FailedPages': 1
        }
        self.mock_storage_service.get_entities.return_value = [existing_entity]
        
        self.service.update_import_progress(import_id, completed_page, success=True)
        
        self.mock_storage_service.get_entities.assert_called_once()
        self.mock_storage_service.upsert_entity.assert_called_once()
        
        # Check updated entity
        call_args = self.mock_storage_service.upsert_entity.call_args
        updated_entity = call_args[1]['entity']
        self.assertEqual(updated_entity['CompletedPages'], 4)  # 3 + 1
        self.assertEqual(updated_entity['LastProcessedPage'], completed_page)

    def test_update_import_progress_failure(self):
        """Test updating import progress with failure."""
        import_id = "test_import_123"
        completed_page = 5
        
        existing_entity = {
            'PartitionKey': 'bulk_import',
            'RowKey': import_id,
            'CompletedPages': 3,
            'FailedPages': 1
        }
        self.mock_storage_service.get_entities.return_value = [existing_entity]
        
        self.service.update_import_progress(import_id, completed_page, success=False)
        
        call_args = self.mock_storage_service.upsert_entity.call_args
        updated_entity = call_args[1]['entity']
        self.assertEqual(updated_entity['FailedPages'], 2)  # 1 + 1
        self.assertEqual(updated_entity['CompletedPages'], 3)  # unchanged

    def test_update_import_progress_entity_not_found(self):
        """Test updating import progress when entity is not found."""
        import_id = "nonexistent_import"
        
        self.mock_storage_service.get_entities.return_value = []
        
        self.service.update_import_progress(import_id, 1)
        
        # Should not call upsert_entity when entity not found
        self.mock_storage_service.upsert_entity.assert_not_called()

    def test_update_import_progress_exception(self):
        """Test handling exceptions in update_import_progress."""
        import_id = "test_import_123"
        
        self.mock_storage_service.get_entities.side_effect = Exception("Storage error")
        
        # Should not raise exception, just log error
        self.service.update_import_progress(import_id, 1)
        
        self.mock_storage_service.upsert_entity.assert_not_called()

    def test_complete_bulk_import_success(self):
        """Test completing bulk import successfully."""
        import_id = "test_import_123"
        final_status = ImportStatus.COMPLETED
        
        existing_entity = {
            'PartitionKey': 'bulk_import',
            'RowKey': import_id,
            'Status': ImportStatus.IN_PROGRESS.value
        }
        self.mock_storage_service.get_entities.return_value = [existing_entity]
        
        self.service.complete_bulk_import(import_id, final_status)
        
        call_args = self.mock_storage_service.upsert_entity.call_args
        updated_entity = call_args[1]['entity']
        self.assertEqual(updated_entity['Status'], final_status.value)
        self.assertIn('EndTime', updated_entity)

    def test_complete_bulk_import_entity_not_found(self):
        """Test completing bulk import when entity is not found."""
        import_id = "nonexistent_import"
        
        self.mock_storage_service.get_entities.return_value = []
        
        self.service.complete_bulk_import(import_id, ImportStatus.COMPLETED)
        
        self.mock_storage_service.upsert_entity.assert_not_called()

    def test_complete_bulk_import_exception(self):
        """Test handling exceptions in complete_bulk_import."""
        import_id = "test_import_123"
        
        self.mock_storage_service.get_entities.side_effect = Exception("Storage error")
        
        self.service.complete_bulk_import(import_id, ImportStatus.COMPLETED)
        
        self.mock_storage_service.upsert_entity.assert_not_called()

    def test_get_import_status_success(self):
        """Test getting import status successfully."""
        import_id = "test_import_123"
        
        entity = {
            'PartitionKey': 'bulk_import',
            'RowKey': import_id,
            'Status': ImportStatus.IN_PROGRESS.value,
            'CompletedPages': 5
        }
        self.mock_storage_service.get_entities.return_value = [entity]
        
        result = self.service.get_import_status(import_id)
        
        self.assertEqual(result['Status'], ImportStatus.IN_PROGRESS.value)
        self.assertEqual(result['CompletedPages'], 5)

    def test_get_import_status_not_found(self):
        """Test getting import status when not found."""
        import_id = "nonexistent_import"
        
        self.mock_storage_service.get_entities.return_value = []
        
        result = self.service.get_import_status(import_id)
        
        self.assertEqual(result, {})

    def test_get_import_status_exception(self):
        """Test handling exceptions in get_import_status."""
        import_id = "test_import_123"
        
        self.mock_storage_service.get_entities.side_effect = Exception("Storage error")
        
        result = self.service.get_import_status(import_id)
        
        self.assertEqual(result, {})

    def test_track_retry_attempt(self):
        """Test tracking retry attempts."""
        operation_type = "index_page"
        identifier = "page_1"
        attempt = 2
        max_attempts = 3
        error = "Connection timeout"
        
        self.service.track_retry_attempt(operation_type, identifier, attempt, max_attempts, error)
        
        self.mock_storage_service.upsert_entity.assert_called_once()
        call_args = self.mock_storage_service.upsert_entity.call_args
        entity = call_args[1]['entity']
        
        self.assertEqual(entity['PartitionKey'], operation_type)
        self.assertEqual(entity['RowKey'], f"{identifier}_{attempt}")
        self.assertEqual(entity['AttemptNumber'], attempt)
        self.assertEqual(entity['ErrorMessage'], error)

    def test_get_failed_operations_success(self):
        """Test getting failed operations."""
        operation_type = "show_details"
        max_age_hours = 24
        
        result = self.service.get_failed_operations(operation_type, max_age_hours)
        
        # Currently returns empty list (placeholder implementation)
        self.assertEqual(result, [])

    def test_get_failed_operations_exception(self):
        """Test handling exceptions in get_failed_operations."""
        operation_type = "show_details"
        
        # Mock an exception during the operation
        with patch('tvbingefriend_show_service.services.monitoring_service.datetime') as mock_datetime:
            mock_datetime.now.side_effect = Exception("Date error")
            
            result = self.service.get_failed_operations(operation_type)
            
            self.assertEqual(result, [])

    def test_update_data_health_with_threshold(self):
        """Test updating data health with threshold."""
        metric_name = "api_response_time"
        value = 150.5
        threshold = 200.0
        
        self.service.update_data_health(metric_name, value, threshold)
        
        self.mock_storage_service.upsert_entity.assert_called_once()
        call_args = self.mock_storage_service.upsert_entity.call_args
        entity = call_args[1]['entity']
        
        self.assertEqual(entity['PartitionKey'], 'health')
        self.assertEqual(entity['RowKey'], metric_name)
        self.assertEqual(entity['Value'], str(value))
        self.assertEqual(entity['Threshold'], str(threshold))
        self.assertTrue(entity['IsHealthy'])  # value <= threshold

    def test_update_data_health_without_threshold(self):
        """Test updating data health without threshold."""
        metric_name = "total_shows"
        value = 1000
        
        self.service.update_data_health(metric_name, value)
        
        call_args = self.mock_storage_service.upsert_entity.call_args
        entity = call_args[1]['entity']
        
        self.assertIsNone(entity['Threshold'])
        self.assertTrue(entity['IsHealthy'])  # Always healthy when no threshold

    def test_update_data_health_unhealthy(self):
        """Test updating data health when value exceeds threshold."""
        metric_name = "error_rate"
        value = 5.0
        threshold = 2.0
        
        self.service.update_data_health(metric_name, value, threshold)
        
        call_args = self.mock_storage_service.upsert_entity.call_args
        entity = call_args[1]['entity']
        
        self.assertFalse(entity['IsHealthy'])  # value > threshold

    def test_check_data_freshness_success(self):
        """Test checking data freshness successfully."""
        max_age_days = 7
        
        result = self.service.check_data_freshness(max_age_days)
        
        self.assertIn('last_check', result)
        self.assertIn('max_age_days', result)
        self.assertIn('is_fresh', result)
        self.assertEqual(result['max_age_days'], max_age_days)
        
        # Should also update data health
        self.mock_storage_service.upsert_entity.assert_called()

    def test_check_data_freshness_exception(self):
        """Test handling exceptions in check_data_freshness."""
        with patch('tvbingefriend_show_service.services.monitoring_service.datetime') as mock_datetime:
            mock_datetime.now.side_effect = Exception("Date error")
            
            result = self.service.check_data_freshness()
            
            self.assertIn('error', result)

    def test_get_health_summary_success(self):
        """Test getting health summary successfully."""
        result = self.service.get_health_summary()
        
        self.assertIn('last_check', result)
        self.assertIn('active_imports', result)
        self.assertIn('failed_operations', result)
        self.assertIn('overall_health', result)
        self.assertEqual(result['overall_health'], 'healthy')

    def test_get_health_summary_exception(self):
        """Test handling exceptions in get_health_summary."""
        with patch('tvbingefriend_show_service.services.monitoring_service.datetime') as mock_datetime:
            mock_datetime.now.side_effect = Exception("Date error")
            
            result = self.service.get_health_summary()
            
            self.assertIn('error', result)


if __name__ == '__main__':
    unittest.main()