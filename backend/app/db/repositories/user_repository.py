"""Repository for User CRUD operations."""
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import UserModel
from .base import BaseRepository


class UserRepository(BaseRepository[UserModel]):
    """Repository for User database operations."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(UserModel, session)
    
    async def get_by_username(self, username: str) -> Optional[UserModel]:
        """Get user by username."""
        result = await self.session.execute(
            select(UserModel).where(UserModel.username == username)
        )
        return result.scalar_one_or_none()
    
    async def get_by_house_id(self, house_id: int) -> Optional[UserModel]:
        """Get user assigned to a specific house."""
        result = await self.session.execute(
            select(UserModel).where(UserModel.house_id == house_id)
        )
        return result.scalar_one_or_none()
    
    async def get_with_house(self, user_id: str) -> Optional[UserModel]:
        """Get user with house relationship loaded."""
        result = await self.session.execute(
            select(UserModel)
            .options(selectinload(UserModel.house))
            .where(UserModel.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_all_with_houses(self) -> List[UserModel]:
        """Get all users with their houses loaded."""
        result = await self.session.execute(
            select(UserModel).options(selectinload(UserModel.house))
        )
        return list(result.scalars().all())
    
    async def is_house_assigned(self, house_id: int, exclude_user_id: Optional[str] = None) -> bool:
        """Check if a house is already assigned to a user."""
        query = select(UserModel).where(UserModel.house_id == house_id)
        if exclude_user_id:
            query = query.where(UserModel.id != exclude_user_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None
    
    async def create_user(
        self,
        username: str,
        password_hash: str,
        house_id: Optional[int] = None,
        is_admin: bool = False
    ) -> UserModel:
        """Create a new user."""
        user = UserModel(
            username=username,
            password_hash=password_hash,
            house_id=house_id,
            is_admin=is_admin
        )
        return await self.create(user)
    
    async def update_password(self, user_id: str, password_hash: str) -> Optional[UserModel]:
        """Update user's password."""
        user = await self.get_by_id(user_id)
        if user:
            user.password_hash = password_hash
            await self.session.flush()
            await self.session.refresh(user)
        return user
    
    async def update_house(self, user_id: str, house_id: Optional[int]) -> Optional[UserModel]:
        """Update user's assigned house."""
        user = await self.get_by_id(user_id)
        if user:
            user.house_id = house_id
            await self.session.flush()
            await self.session.refresh(user)
        return user
    
    async def get_admins(self) -> List[UserModel]:
        """Get all admin users."""
        result = await self.session.execute(
            select(UserModel).where(UserModel.is_admin == True)
        )
        return list(result.scalars().all())
