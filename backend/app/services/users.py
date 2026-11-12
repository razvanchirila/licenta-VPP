"""A house can belong to at most one account; the checks here turn that rule into 400s."""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UserModel
from app.db.repositories import HouseRepository, UserRepository
from app.services.auth import hash_password


async def create_user(
    session: AsyncSession, username: str, password: str, house_id: int | None = None, is_admin: bool = False
) -> UserModel | None:
    repo = UserRepository(session)
    if await repo.get_by_username(username) is not None:
        return None
    user = UserModel(username=username, password_hash=hash_password(password), house_id=house_id, is_admin=is_admin)
    try:
        async with session.begin_nested():
            session.add(user)
    except IntegrityError:
        # a request running at the same time took the name or the house after the checks had passed
        if house_id is not None:
            await ensure_house_assignable(session, house_id)
        return None
    return user


async def ensure_house_assignable(session: AsyncSession, house_id: int, exclude_user_id: str | None = None) -> None:
    if await HouseRepository(session).get_by_id(house_id) is None:
        raise HTTPException(400, f"Casa {house_id} nu exista")
    if await UserRepository(session).is_house_assigned(house_id, exclude_user_id):
        raise HTTPException(400, f"Casa {house_id} e deja asignata altui utilizator")


async def update_user(session: AsyncSession, user: UserModel, password: str | None, house_id: int | None,
                      is_admin: bool | None) -> UserModel:
    if password:
        user.password_hash = hash_password(password)
    if house_id is not None:
        if house_id == 0:
            user.house_id = None
        else:
            await ensure_house_assignable(session, house_id, exclude_user_id=user.id)
            user.house_id = house_id
    if is_admin is not None:
        user.is_admin = is_admin
    try:
        await session.flush()
    except IntegrityError:
        raise HTTPException(400, f"Casa {house_id} e deja asignata altui utilizator") from None
    return user
