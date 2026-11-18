from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.schemas import LoginRequest, RegisterRequest
from app.db.database import get_session
from app.db.models import UserModel
from app.db.repositories import UserRepository
from app.services.auth import create_access_token, verify_password
from app.services.rate_limit import login_failures, registrations
from app.services.serializers import user_dict
from app.services.users import create_user
from app.settings import settings

router = APIRouter(prefix="/auth", tags=["auth"])


def _too_many(window) -> HTTPException:
    return HTTPException(429, "Prea multe incercari, mai incearca peste cateva minute",
                         headers={"Retry-After": str(int(window.window))})


@router.post("/login")
async def login(body: LoginRequest, session: AsyncSession = Depends(get_session)):
    key = body.username.lower()
    if login_failures.count(key) >= settings.login_max_failures:
        raise _too_many(login_failures)
    user = await UserRepository(session).get_by_username(body.username)
    if user is None or not verify_password(body.password, user.password_hash):
        login_failures.hit(key)
        raise HTTPException(401, "Utilizator sau parola gresita")
    login_failures.reset(key)
    return {
        "access_token": create_access_token(user.id),
        "token_type": "bearer",
        "expires_in": int(settings.jwt_expire_hours * 3600),
        "user_id": user.id,
        "username": user.username,
        "house_id": user.house_id,
        "is_admin": user.is_admin,
    }


@router.post("/register", status_code=201)
async def register(body: RegisterRequest, session: AsyncSession = Depends(get_session)):
    if registrations.count("all") >= settings.register_max_per_hour:
        raise _too_many(registrations)
    registrations.hit("all")
    user = await create_user(session, body.username, body.password)
    if user is None:
        raise HTTPException(400, "Numele de utilizator exista deja")
    return {"user_id": user.id, "username": user.username, "house_id": None,
            "message": "Cont creat. Un administrator trebuie sa iti asigneze o casa."}


@router.get("/me")
async def me(user: UserModel = Depends(get_current_user)):
    return user_dict(user)
