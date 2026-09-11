"""JWT authentication middleware for User API."""
from typing import Optional
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.services.auth import AuthService


security = HTTPBearer()


class JWTBearer(HTTPBearer):
    """Custom JWT Bearer authentication."""
    
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
    
    async def __call__(self, request: Request) -> Optional[dict]:
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        
        if not credentials:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        if credentials.scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")
        
        payload = AuthService.verify_token(credentials.credentials)
        
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        return payload


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Dependency to get current user from JWT token.
    
    Returns:
        dict with user_id, house_id, is_admin
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    payload = AuthService.verify_token(credentials.credentials)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return {
        "user_id": payload.get("sub"),
        "house_id": payload.get("house_id"),
        "is_admin": payload.get("is_admin", False)
    }


def require_house(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Dependency that requires user to have an assigned house.
    """
    if not current_user.get("house_id"):
        raise HTTPException(
            status_code=403, 
            detail="No house assigned to this user"
        )
    return current_user
