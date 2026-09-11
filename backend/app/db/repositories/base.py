"""Base repository class with common CRUD operations."""
from typing import Generic, TypeVar, Type, List, Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Base repository providing common CRUD operations.
    
    Attributes:
        model: The SQLAlchemy model class
        session: The async database session
    """
    
    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session
    
    async def get_by_id(self, id: int) -> Optional[ModelType]:
        """Get a single record by ID."""
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()
    
    async def get_all(self) -> List[ModelType]:
        """Get all records."""
        result = await self.session.execute(select(self.model))
        return list(result.scalars().all())
    
    async def create(self, obj: ModelType) -> ModelType:
        """Create a new record."""
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj
    
    async def update(self, obj: ModelType) -> ModelType:
        """Update an existing record."""
        await self.session.flush()
        await self.session.refresh(obj)
        return obj
    
    async def delete(self, id: int) -> bool:
        """Delete a record by ID."""
        result = await self.session.execute(
            delete(self.model).where(self.model.id == id)
        )
        return result.rowcount > 0
    
    async def delete_obj(self, obj: ModelType) -> None:
        """Delete a record object."""
        await self.session.delete(obj)
        await self.session.flush()
    
    async def bulk_create(self, objects: List[ModelType]) -> List[ModelType]:
        """Create multiple records in a single transaction."""
        self.session.add_all(objects)
        await self.session.flush()
        for obj in objects:
            await self.session.refresh(obj)
        return objects
