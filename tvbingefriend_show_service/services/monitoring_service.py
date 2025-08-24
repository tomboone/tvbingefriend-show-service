"""Service for monitoring import progress and data freshness."""
import logging
from datetime import datetime, timedelta, UTC
from typing import Any, Dict, List, Optional
from enum import Enum

from tvbingefriend_azure_storage_service import StorageService  # type: ignore

from tvbingefriend_show_service.config import (
    STORAGE_CONNECTION_STRING,
)


class ImportStatus(Enum):
    """Import operation status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress" 
    COMPLETED = "completed"
    FAILED = "failed"


# noinspection PyMethodMayBeStatic
class MonitoringService:
    """Service for tracking import progress and monitoring data quality."""
    
    def __init__(self, storage_service: Optional[StorageService] = None) -> None:
        self.storage_service = storage_service or StorageService(STORAGE_CONNECTION_STRING)
        self.import_tracking_table = "importtracking"
        self.retry_tracking_table = "retrytracking"
        self.data_health_table = "datahealth"
    
    def start_bulk_import_tracking(
            self, import_id: str, start_page: int = 0, estimated_pages: Optional[int] = None
    ) -> None:
        """Start tracking a bulk import operation.
        
        Args:
            import_id: Unique identifier for this import operation
            start_page: Starting page number
            estimated_pages: Estimated total pages (if known)
        """
        entity = {
            "PartitionKey": "bulk_import",
            "RowKey": import_id,
            "Status": ImportStatus.IN_PROGRESS.value,
            "StartTime": datetime.now(UTC).isoformat(),
            "StartPage": start_page,
            "EstimatedPages": estimated_pages or -1,
            "CompletedPages": 0,
            "FailedPages": 0,
            "LastActivityTime": datetime.now(UTC).isoformat()
        }
        
        self.storage_service.upsert_entity(
            table_name=self.import_tracking_table,
            entity=entity
        )
        logging.info(f"Started tracking bulk import: {import_id}")
    
    def update_import_progress(self, import_id: str, completed_page: int, success: bool = True) -> None:
        """Update progress for a bulk import operation.
        
        Args:
            import_id: Import operation identifier
            completed_page: Page number that was just completed
            success: Whether the page was processed successfully
        """
        try:
            # Get current tracking entity
            entities = self.storage_service.get_entities(
                table_name=self.import_tracking_table,
                filter_query=f"PartitionKey eq 'bulk_import' and RowKey eq '{import_id}'"
            )
            entity = entities[0] if entities else None
            
            if entity is None:
                logging.error(f"Import tracking entity not found for import_id: {import_id}")
                return
            
            # Update counters
            if success:
                entity["CompletedPages"] = entity.get("CompletedPages", 0) + 1
            else:
                entity["FailedPages"] = entity.get("FailedPages", 0) + 1
            
            entity["LastActivityTime"] = datetime.now(UTC).isoformat()
            entity["LastProcessedPage"] = completed_page
            
            self.storage_service.upsert_entity(
                table_name=self.import_tracking_table,
                entity=entity
            )
            
        except Exception as e:
            logging.error(f"Failed to update import progress for {import_id}: {e}")
    
    def complete_bulk_import(self, import_id: str, final_status: ImportStatus) -> None:
        """Mark a bulk import as completed.
        
        Args:
            import_id: Import operation identifier
            final_status: Final status of the import
        """
        try:
            entities = self.storage_service.get_entities(
                table_name=self.import_tracking_table,
                filter_query=f"PartitionKey eq 'bulk_import' and RowKey eq '{import_id}'"
            )
            entity = entities[0] if entities else None
            
            if entity is None:
                logging.error(f"Import tracking entity not found for import_id: {import_id}")
                return
            
            entity["Status"] = final_status.value
            entity["EndTime"] = datetime.now(UTC).isoformat()
            entity["LastActivityTime"] = datetime.now(UTC).isoformat()
            
            self.storage_service.upsert_entity(
                table_name=self.import_tracking_table,
                entity=entity
            )
            
            logging.info(f"Bulk import {import_id} completed with status: {final_status.value}")
            
        except Exception as e:
            logging.error(f"Failed to complete import tracking for {import_id}: {e}")
    
    def get_import_status(self, import_id: str) -> Dict[str, Any]:
        """Get status of a bulk import operation.
        
        Args:
            import_id: Import operation identifier
            
        Returns:
            Dictionary with import status information
        """
        try:
            entities = self.storage_service.get_entities(
                table_name=self.import_tracking_table,
                filter_query=f"PartitionKey eq 'bulk_import' and RowKey eq '{import_id}'"
            )
            entity = entities[0] if entities else None
            return dict(entity) if entity else {}
        except Exception as e:
            logging.error(f"Failed to get import status for {import_id}: {e}")
            return {}
    
    def track_retry_attempt(
            self, operation_type: str, identifier: str, attempt: int, max_attempts: int, error: str
    ) -> None:
        """Track retry attempts for failed operations.
        
        Args:
            operation_type: Type of operation (e.g., 'index_page', 'show_details')
            identifier: Unique identifier for the operation
            attempt: Current attempt number
            max_attempts: Maximum allowed attempts
            error: Error message from the failed attempt
        """
        entity = {
            "PartitionKey": operation_type,
            "RowKey": f"{identifier}_{attempt}",
            "Identifier": identifier,
            "AttemptNumber": attempt,
            "MaxAttempts": max_attempts,
            "ErrorMessage": error,
            "AttemptTime": datetime.now(UTC).isoformat(),
            "NextRetryTime": (datetime.now(UTC) + timedelta(minutes=2**attempt)).isoformat()  # Exponential backoff
        }
        
        self.storage_service.upsert_entity(
            table_name=self.retry_tracking_table,
            entity=entity
        )
        
        logging.info(f"Tracked retry attempt {attempt}/{max_attempts} for {operation_type}:{identifier}")
    
    def get_failed_operations(self, operation_type: str, max_age_hours: int = 24) -> List[Dict[str, Any]]:
        """Get operations that have failed and may need retry.
        
        Args:
            operation_type: Type of operation to check
            max_age_hours: Only return failures within this many hours
            
        Returns:
            List of failed operations that need attention
        """
        # This would require querying the retry tracking table
        # Implementation depends on your Azure Storage Service query capabilities
        try:
            # Get entities from retry tracking table for this operation type
            cutoff_time = datetime.now(UTC) - timedelta(hours=max_age_hours)
            
            # Note: This is a simplified implementation
            # You might need to implement proper querying in your StorageService
            logging.info(f"Checking for failed {operation_type} operations since {cutoff_time}")
            return []  # Placeholder - implement based on your storage service query capabilities
            
        except Exception as e:
            logging.error(f"Failed to get failed operations for {operation_type}: {e}")
            return []
    
    def update_data_health(self, metric_name: str, value: Any, threshold: Optional[Any] = None) -> None:
        """Update data health metrics.
        
        Args:
            metric_name: Name of the health metric
            value: Current value of the metric
            threshold: Alert threshold (if applicable)
        """
        entity = {
            "PartitionKey": "health",
            "RowKey": metric_name,
            "Value": str(value),
            "Threshold": str(threshold) if threshold else None,
            "LastUpdated": datetime.now(UTC).isoformat(),
            "IsHealthy": threshold is None or (isinstance(value, (int, float)) and value <= threshold)
        }
        
        self.storage_service.upsert_entity(
            table_name=self.data_health_table,
            entity=entity
        )
    
    def check_data_freshness(self, max_age_days: int = 7) -> Dict[str, Any]:
        """Check data freshness and return health status.
        
        Args:
            max_age_days: Maximum acceptable age for data in days
            
        Returns:
            Dictionary with freshness status
        """
        try:
            cutoff_time = datetime.now(UTC) - timedelta(days=max_age_days)
            
            # This is a simplified check - you might want to implement
            # more sophisticated freshness checking based on your needs
            health_status = {
                "last_check": datetime.now(UTC).isoformat(),
                "max_age_days": max_age_days,
                "cutoff_time": cutoff_time.isoformat(),
                "is_fresh": True,  # Placeholder
                "stale_count": 0,  # Placeholder
                "total_shows": 0   # Placeholder
            }
            
            # Update health metric
            self.update_data_health("data_freshness_days", max_age_days, max_age_days)
            
            return health_status
            
        except Exception as e:
            logging.error(f"Failed to check data freshness: {e}")
            return {"error": str(e)}
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get overall system health summary.
        
        Returns:
            Dictionary with system health information
        """
        try:
            # Get recent imports
            # Get failed operations
            # Get data freshness
            # This would aggregate information from various tracking tables
            
            summary = {
                "last_check": datetime.now(UTC).isoformat(),
                "active_imports": 0,  # Count of in-progress imports
                "failed_operations": 0,  # Count of failed operations needing attention
                "data_freshness": "unknown",  # Overall freshness status
                "overall_health": "healthy"  # Overall system health
            }
            
            return summary
            
        except Exception as e:
            logging.error(f"Failed to get health summary: {e}")
            return {"error": str(e)}
