from __future__ import annotations

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.settings import settings

ALGORITHM = "HS256"
MAX_PASSWORD_BYTES = 72   # bcrypt limit; longer input raises in bcrypt >= 5


def hash_password(password: str) -> str:
    raw = password.encode("utf-8")
    if len(raw) > MAX_PASSWORD_BYTES:
        raise ValueError(f"parola nu poate depasi {MAX_PASSWORD_BYTES} de octeti")
    return bcrypt.hashpw(raw, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    raw = password.encode("utf-8")
    if len(raw) > MAX_PASSWORD_BYTES:
        return False
    try:
        return bcrypt.checkpw(raw, password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: str, expires: timedelta | None = None) -> str:
    settings.require_secret()
    now = datetime.now(UTC)
    exp = now + (expires or timedelta(hours=settings.jwt_expire_hours))
    return jwt.encode({"sub": user_id, "iat": now, "exp": exp}, settings.jwt_secret, algorithm=ALGORITHM)


def decode_token(token: str) -> str | None:
    settings.require_secret()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
    sub = payload.get("sub")
    return sub if isinstance(sub, str) else None
