"""Authentication service with JWT and bcrypt."""
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import bcrypt
from jose import jwt, JWTError


# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "vpp-simulator-secret-key-change-in-production")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24


class AuthService:
    """Service for authentication operations."""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        try:
            password_bytes = plain_password.encode('utf-8')
            hashed_bytes = hashed_password.encode('utf-8')
            return bcrypt.checkpw(password_bytes, hashed_bytes)
        except Exception:
            return False
    
    @staticmethod
    def create_access_token(
        user_id: str,
        house_id: Optional[int] = None,
        is_admin: bool = False,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT access token.
        
        Args:
            user_id: User's UUID
            house_id: User's assigned house ID (None for admins without house)
            is_admin: Whether user is admin
            expires_delta: Custom expiration time
        
        Returns:
            Encoded JWT token
        """
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS)
        
        payload = {
            "sub": user_id,
            "house_id": house_id,
            "is_admin": is_admin,
            "exp": expire,
            "iat": datetime.utcnow()
        }
        
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    
    @staticmethod
    def verify_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode a JWT token.
        
        Args:
            token: JWT token string
        
        Returns:
            Decoded payload dict or None if invalid
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError:
            return None
    
    @staticmethod
    def get_user_id_from_token(token: str) -> Optional[str]:
        """Extract user_id from token."""
        payload = AuthService.verify_token(token)
        if payload:
            return payload.get("sub")
        return None
    
    @staticmethod
    def get_house_id_from_token(token: str) -> Optional[int]:
        """Extract house_id from token."""
        payload = AuthService.verify_token(token)
        if payload:
            return payload.get("house_id")
        return None
    
    @staticmethod
    def is_token_expired(token: str) -> bool:
        """Check if token is expired."""
        payload = AuthService.verify_token(token)
        if not payload:
            return True
        
        exp = payload.get("exp")
        if not exp:
            return True
        
        return datetime.utcnow() > datetime.fromtimestamp(exp)
