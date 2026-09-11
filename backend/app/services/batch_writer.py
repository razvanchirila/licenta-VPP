"""Batch Writer Service - efficient batch persistence of device energy data."""
import logging
import asyncio
from typing import Dict, List, Optional
from app.models.device import Device

logger = logging.getLogger(__name__)


class BatchWriter:
    """
    Service for batching and persisting device energy updates.
    
    Features:
    - Batches updates within a configurable window
    - Applies minimum energy threshold to avoid micro-writes
    - Uses bulk updates for efficiency
    """
    
    BATCH_WINDOW_SECONDS: float = 1.0
    ENERGY_THRESHOLD_KWH: float = 0.0001
    
    def __init__(self):
        self._pending_updates: Dict[int, Dict] = {}  # device_id -> update data
        self._last_flush_time: float = 0
    
    def queue_update(self, device: Device) -> None:
        """
        Add a device to the pending update queue.
        
        Args:
            device: Device with updated energy data
        """
        self._pending_updates[device.id] = {
            'id': device.id,
            'accumulated_energy_kwh': device.accumulated_energy_kwh,
            'status_on': device.status_on,
            'last_state_change_ts': device.last_state_change_ts
        }
    
    def should_persist(self, energy_kwh: float) -> bool:
        """
        Check if energy exceeds the persistence threshold.
        
        Args:
            energy_kwh: Energy amount to check
            
        Returns:
            True if energy >= threshold
        """
        return energy_kwh >= self.ENERGY_THRESHOLD_KWH
    
    async def flush(self) -> int:
        """
        Persist all pending updates to database.
        
        Returns:
            Number of devices updated
        """
        if not self._pending_updates:
            return 0
        
        updates = list(self._pending_updates.values())
        self._pending_updates.clear()
        
        try:
            from app.db.database import get_session_context
            from app.db.repositories import DeviceRepository
            
            async with get_session_context() as session:
                device_repo = DeviceRepository(session)
                count = await device_repo.bulk_update_energy(updates)
                logger.debug(f"Flushed {count} device updates to database")
                return count
                
        except Exception as e:
            logger.error(f"Failed to flush updates: {e}")
            # Re-queue failed updates for retry
            for update in updates:
                self._pending_updates[update['id']] = update
            raise
    
    def get_pending_count(self) -> int:
        """Get number of pending updates."""
        return len(self._pending_updates)
    
    def clear(self) -> None:
        """Clear all pending updates without persisting."""
        self._pending_updates.clear()


# Global batch writer instance
batch_writer = BatchWriter()
