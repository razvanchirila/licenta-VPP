from datetime import datetime
from typing import Any

from sqlalchemy import and_, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import DeviceModel, EnergyLogModel
from .base import BaseRepository


class EnergyLogRepository(BaseRepository[EnergyLogModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(EnergyLogModel, session)

    def log_event(self, device_id: int, event_type: str, sim_ts: datetime, energy_kwh: float = 0.0,
                  details: str | None = None) -> EnergyLogModel:
        log = EnergyLogModel(device_id=device_id, timestamp=sim_ts, energy_kwh=energy_kwh,
                             event_type=event_type, details=details)
        self.session.add(log)
        return log

    def _house_filter(self, house_id: int, start: datetime, end: datetime):
        return and_(DeviceModel.house_id == house_id, EnergyLogModel.timestamp >= start,
                    EnergyLogModel.timestamp <= end)

    async def get_aggregated_by_device(self, house_id: int, start_date: datetime,
                                       end_date: datetime) -> list[dict[str, Any]]:
        total = func.sum(EnergyLogModel.energy_kwh)
        result = await self.session.execute(
            select(EnergyLogModel.device_id, DeviceModel.name.label("device_name"), total.label("total_kwh"))
            .join(DeviceModel, EnergyLogModel.device_id == DeviceModel.id)
            .where(self._house_filter(house_id, start_date, end_date))
            .group_by(EnergyLogModel.device_id, DeviceModel.name)
            .order_by(total.desc())
        )
        return [{"device_id": r.device_id, "device_name": r.device_name, "total_kwh": float(r.total_kwh or 0.0)}
                for r in result.all()]

    async def get_aggregated_by_day(self, house_id: int, start_date: datetime,
                                    end_date: datetime) -> list[dict[str, Any]]:
        day = func.date(EnergyLogModel.timestamp)
        result = await self.session.execute(
            select(day.label("log_date"), func.sum(EnergyLogModel.energy_kwh).label("total_kwh"))
            .join(DeviceModel, EnergyLogModel.device_id == DeviceModel.id)
            .where(self._house_filter(house_id, start_date, end_date))
            .group_by(day).order_by(day)
        )
        return [{"date": _as_date(r.log_date), "total_kwh": float(r.total_kwh or 0.0)} for r in result.all()]

    async def get_aggregated_by_hour(self, house_id: int, start_date: datetime,
                                     end_date: datetime) -> list[dict[str, Any]]:
        day = func.date(EnergyLogModel.timestamp)
        hour = extract("hour", EnergyLogModel.timestamp)
        result = await self.session.execute(
            select(day.label("log_date"), hour.label("hour"), func.sum(EnergyLogModel.energy_kwh).label("total_kwh"))
            .join(DeviceModel, EnergyLogModel.device_id == DeviceModel.id)
            .where(self._house_filter(house_id, start_date, end_date))
            .group_by(day, hour).order_by(day, hour)
        )
        return [{"date": _as_date(r.log_date), "hour": int(r.hour), "total_kwh": float(r.total_kwh or 0.0)}
                for r in result.all()]

    async def get_total_for_period(self, house_id: int, start_date: datetime, end_date: datetime) -> float:
        result = await self.session.execute(
            select(func.sum(EnergyLogModel.energy_kwh))
            .join(DeviceModel, EnergyLogModel.device_id == DeviceModel.id)
            .where(self._house_filter(house_id, start_date, end_date))
        )
        return float(result.scalar() or 0.0)


def _as_date(value):
    """SQLite returns date() as 'YYYY-MM-DD' text, other backends as date objects."""
    if isinstance(value, str):
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    return value
