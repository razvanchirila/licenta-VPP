"""Repository for EnergyLog audit operations."""
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_, func, extract
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import EnergyLogModel, DeviceModel
from .base import BaseRepository


class EnergyLogRepository(BaseRepository[EnergyLogModel]):
    """Repository for energy log (audit) database operations."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(EnergyLogModel, session)
    
    async def get_by_device_id(
        self, 
        device_id: int, 
        limit: int = 100
    ) -> List[EnergyLogModel]:
        """Get energy logs for a specific device."""
        result = await self.session.execute(
            select(EnergyLogModel)
            .where(EnergyLogModel.device_id == device_id)
            .order_by(EnergyLogModel.timestamp.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_by_event_type(
        self, 
        event_type: str, 
        limit: int = 100
    ) -> List[EnergyLogModel]:
        """Get energy logs by event type."""
        result = await self.session.execute(
            select(EnergyLogModel)
            .where(EnergyLogModel.event_type == event_type)
            .order_by(EnergyLogModel.timestamp.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        device_id: Optional[int] = None
    ) -> List[EnergyLogModel]:
        """Get energy logs within a date range."""
        conditions = [
            EnergyLogModel.timestamp >= start_date,
            EnergyLogModel.timestamp <= end_date
        ]
        
        if device_id is not None:
            conditions.append(EnergyLogModel.device_id == device_id)
        
        result = await self.session.execute(
            select(EnergyLogModel)
            .where(and_(*conditions))
            .order_by(EnergyLogModel.timestamp.desc())
        )
        return list(result.scalars().all())
    
    async def log_toggle_on(
        self, 
        device_id: int, 
        details: Optional[str] = None
    ) -> EnergyLogModel:
        """Log a device toggle ON event."""
        log = EnergyLogModel(
            device_id=device_id,
            energy_kwh=0.0,  # No energy calculated on toggle ON
            event_type="toggle_on",
            details=details
        )
        return await self.create(log)
    
    async def log_toggle_off(
        self, 
        device_id: int, 
        energy_kwh: float,
        details: Optional[str] = None
    ) -> EnergyLogModel:
        """Log a device toggle OFF event with calculated energy."""
        log = EnergyLogModel(
            device_id=device_id,
            energy_kwh=energy_kwh,
            event_type="toggle_off",
            details=details
        )
        return await self.create(log)
    
    async def log_checkpoint(
        self, 
        device_id: int, 
        energy_kwh: float,
        details: Optional[str] = None
    ) -> EnergyLogModel:
        """Log a checkpoint event (periodic persistence)."""
        log = EnergyLogModel(
            device_id=device_id,
            energy_kwh=energy_kwh,
            event_type="checkpoint",
            details=details
        )
        return await self.create(log)
    
    async def bulk_log_checkpoint(
        self, 
        logs: List[dict]
    ) -> List[EnergyLogModel]:
        """
        Bulk create checkpoint logs.
        
        Args:
            logs: List of dicts with device_id, energy_kwh, and optional details
        """
        log_objects = [
            EnergyLogModel(
                device_id=log['device_id'],
                energy_kwh=log['energy_kwh'],
                event_type="checkpoint",
                details=log.get('details')
            )
            for log in logs
        ]
        return await self.bulk_create(log_objects)
    
    # ============ Analytics Aggregation Methods ============
    
    async def get_aggregated_by_device(
        self,
        house_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """
        Aggregate energy consumption by device for a house within a time period.
        
        Returns list of dicts with device_id, device_name, total_kwh ordered by consumption DESC.
        """
        result = await self.session.execute(
            select(
                EnergyLogModel.device_id,
                DeviceModel.name.label('device_name'),
                func.sum(EnergyLogModel.energy_kwh).label('total_kwh')
            )
            .join(DeviceModel, EnergyLogModel.device_id == DeviceModel.id)
            .where(
                and_(
                    DeviceModel.house_id == house_id,
                    EnergyLogModel.timestamp >= start_date,
                    EnergyLogModel.timestamp <= end_date
                )
            )
            .group_by(EnergyLogModel.device_id, DeviceModel.name)
            .order_by(func.sum(EnergyLogModel.energy_kwh).desc())
        )
        
        return [
            {
                'device_id': row.device_id,
                'device_name': row.device_name,
                'total_kwh': float(row.total_kwh) if row.total_kwh else 0.0
            }
            for row in result.all()
        ]
    
    async def get_aggregated_by_day(
        self,
        house_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """
        Aggregate energy consumption by calendar day for a house.
        
        Returns list of dicts with date and total_kwh ordered chronologically.
        """
        result = await self.session.execute(
            select(
                func.date(EnergyLogModel.timestamp).label('log_date'),
                func.sum(EnergyLogModel.energy_kwh).label('total_kwh')
            )
            .join(DeviceModel, EnergyLogModel.device_id == DeviceModel.id)
            .where(
                and_(
                    DeviceModel.house_id == house_id,
                    EnergyLogModel.timestamp >= start_date,
                    EnergyLogModel.timestamp <= end_date
                )
            )
            .group_by(func.date(EnergyLogModel.timestamp))
            .order_by(func.date(EnergyLogModel.timestamp))
        )
        
        return [
            {
                'date': row.log_date if isinstance(row.log_date, date) else row.log_date,
                'total_kwh': float(row.total_kwh) if row.total_kwh else 0.0
            }
            for row in result.all()
        ]
    
    async def get_aggregated_by_month(
        self,
        house_id: int,
        year: int
    ) -> List[Dict[str, Any]]:
        """
        Aggregate energy consumption by month for a house in a given year.
        
        Returns list of dicts with year, month, and total_kwh.
        """
        result = await self.session.execute(
            select(
                extract('year', EnergyLogModel.timestamp).label('year'),
                extract('month', EnergyLogModel.timestamp).label('month'),
                func.sum(EnergyLogModel.energy_kwh).label('total_kwh')
            )
            .join(DeviceModel, EnergyLogModel.device_id == DeviceModel.id)
            .where(
                and_(
                    DeviceModel.house_id == house_id,
                    extract('year', EnergyLogModel.timestamp) == year
                )
            )
            .group_by(
                extract('year', EnergyLogModel.timestamp),
                extract('month', EnergyLogModel.timestamp)
            )
            .order_by(
                extract('year', EnergyLogModel.timestamp),
                extract('month', EnergyLogModel.timestamp)
            )
        )
        
        return [
            {
                'year': int(row.year),
                'month': int(row.month),
                'total_kwh': float(row.total_kwh) if row.total_kwh else 0.0
            }
            for row in result.all()
        ]
    
    async def get_total_for_period(
        self,
        house_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> float:
        """
        Get total energy consumption for a house within a time period.
        
        Returns total kWh as float.
        """
        result = await self.session.execute(
            select(func.sum(EnergyLogModel.energy_kwh).label('total'))
            .join(DeviceModel, EnergyLogModel.device_id == DeviceModel.id)
            .where(
                and_(
                    DeviceModel.house_id == house_id,
                    EnergyLogModel.timestamp >= start_date,
                    EnergyLogModel.timestamp <= end_date
                )
            )
        )
        
        row = result.first()
        return float(row.total) if row and row.total else 0.0
    
    async def get_aggregated_by_hour(
        self,
        house_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """
        Aggregate energy consumption by hour for a house (for short-range charts).
        
        Returns list of dicts with datetime and total_kwh.
        """
        result = await self.session.execute(
            select(
                func.date(EnergyLogModel.timestamp).label('log_date'),
                extract('hour', EnergyLogModel.timestamp).label('hour'),
                func.sum(EnergyLogModel.energy_kwh).label('total_kwh')
            )
            .join(DeviceModel, EnergyLogModel.device_id == DeviceModel.id)
            .where(
                and_(
                    DeviceModel.house_id == house_id,
                    EnergyLogModel.timestamp >= start_date,
                    EnergyLogModel.timestamp <= end_date
                )
            )
            .group_by(
                func.date(EnergyLogModel.timestamp),
                extract('hour', EnergyLogModel.timestamp)
            )
            .order_by(
                func.date(EnergyLogModel.timestamp),
                extract('hour', EnergyLogModel.timestamp)
            )
        )
        
        return [
            {
                'date': row.log_date,
                'hour': int(row.hour),
                'total_kwh': float(row.total_kwh) if row.total_kwh else 0.0
            }
            for row in result.all()
        ]
