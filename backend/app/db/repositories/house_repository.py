"""Houses with all relations in a fixed number of queries (selectinload), never one per house."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import HouseModel
from .base import BaseRepository

_RELATIONS = (
    selectinload(HouseModel.battery),
    selectinload(HouseModel.devices),
    selectinload(HouseModel.trading_preferences),
    selectinload(HouseModel.wallet),
    selectinload(HouseModel.vpp_reserve),
    selectinload(HouseModel.user),
)


class HouseRepository(BaseRepository[HouseModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(HouseModel, session)

    async def get_by_id_with_relations(self, house_id: int) -> HouseModel | None:
        result = await self.session.execute(select(HouseModel).options(*_RELATIONS).where(HouseModel.id == house_id))
        return result.scalar_one_or_none()

    async def get_all_with_relations(self) -> list[HouseModel]:
        """Ordered by id: the order the simulation arrays use."""
        result = await self.session.execute(select(HouseModel).options(*_RELATIONS).order_by(HouseModel.id))
        return list(result.scalars().all())
