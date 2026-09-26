from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import DeviceModel
from .base import BaseRepository


class DeviceRepository(BaseRepository[DeviceModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(DeviceModel, session)

    async def get_by_house_id(self, house_id: int) -> list[DeviceModel]:
        result = await self.session.execute(
            select(DeviceModel).where(DeviceModel.house_id == house_id).order_by(DeviceModel.id)
        )
        return list(result.scalars().all())
