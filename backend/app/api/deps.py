from __future__ import annotations

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session, get_session_context
from app.db.models import HouseModel, UserModel
from app.db.repositories import HouseRepository, UserRepository
from app.services.auth import decode_token

bearer = HTTPBearer(auto_error=False)


async def _user_from_token(token: str | None, session: AsyncSession) -> UserModel | None:
    """Re-read from the DB on every request so role/house changes apply immediately."""
    user_id = decode_token(token) if token else None
    return await UserRepository(session).get_with_house(user_id) if user_id else None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: AsyncSession = Depends(get_session),
) -> UserModel:
    token = credentials.credentials if credentials else None
    user = await _user_from_token(token, session)
    if user is None:
        detail = "Autentificare necesara" if not token else "Token invalid sau expirat"
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail, headers={"WWW-Authenticate": "Bearer"})
    return user


async def get_ws_user(token: str | None = Query(default=None)) -> UserModel | None:
    """WebSocket clients cannot set headers, so the token comes as ?token=...; None when it is missing or invalid."""
    # not Depends(get_session): that session would stay open, with its pool connection, until the socket closes
    async with get_session_context() as session:
        return await _user_from_token(token, session)


def require_admin(user: UserModel = Depends(get_current_user)) -> UserModel:
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Doar administratorul poate face asta")
    return user


def require_house(user: UserModel = Depends(get_current_user)) -> int:
    if user.house_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Utilizatorul nu are o casa asignata")
    return user.house_id


def check_house_access(user: UserModel, house_id: int) -> None:
    if not user.is_admin and user.house_id != house_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Acces permis doar la propria casa")


def require_house_access(house_id: int, user: UserModel = Depends(get_current_user)) -> UserModel:
    check_house_access(user, house_id)
    return user


async def load_house(session: AsyncSession, house_id: int) -> HouseModel:
    house = await HouseRepository(session).get_by_id_with_relations(house_id)
    if house is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Casa {house_id} nu exista")
    return house
