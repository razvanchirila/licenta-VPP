"""Authentication routes for User API."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.db.repositories import UserRepository
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["authentication"])


class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86400  # 24 hours in seconds
    user_id: str
    house_id: int | None = None


@router.post("/register", response_model=dict)
async def register(
    request: RegisterRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    Register a new user.
    Note: House assignment is done by admin separately.
    """
    user_repo = UserRepository(session)
    
    # Check if username exists
    existing = await user_repo.get_by_username(request.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Hash password and create user
    password_hash = AuthService.hash_password(request.password)
    user = await user_repo.create_user(
        username=request.username,
        password_hash=password_hash
    )
    
    return {
        "user_id": user.id,
        "username": user.username,
        "message": "User created successfully. Contact admin for house assignment."
    }


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    Login and get JWT token.
    """
    user_repo = UserRepository(session)
    
    # Find user
    user = await user_repo.get_by_username(request.username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Verify password
    if not AuthService.verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create token
    token = AuthService.create_access_token(
        user_id=user.id,
        house_id=user.house_id,
        is_admin=user.is_admin
    )
    
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        house_id=user.house_id
    )
