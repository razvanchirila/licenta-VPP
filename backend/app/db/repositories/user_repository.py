from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import UserModel
from .base import BaseRepository


class UserRepository(BaseRepository[UserModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(UserModel, session)

    async def get_by_username(self, username: str) -> UserModel | None:
        result = await self.session.execute(select(UserModel).where(UserModel.username == username))
        return result.scalar_one_or_none()

    async def get_with_house(self, user_id: str) -> UserModel | None:
        result = await self.session.execute(
            select(UserModel).options(selectinload(UserModel.house)).where(UserModel.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_all_with_houses(self) -> list[UserModel]:
        result = await self.session.execute(
            select(UserModel).options(selectinload(UserModel.house)).order_by(UserModel.created_at, UserModel.username)
        )
        return list(result.scalars().all())

    async def is_house_assigned(self, house_id: int, exclude_user_id: str | None = None) -> bool:
        query = select(UserModel.id).where(UserModel.house_id == house_id)
        if exclude_user_id:
            query = query.where(UserModel.id != exclude_user_id)
        return (await self.session.execute(query)).first() is not None
