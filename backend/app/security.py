from datetime import datetime, timedelta

import bcrypt
import jwt

from app.config import get_settings
from app.db_types import utcnow

ALGORITHM = "HS256"

# Used to spend the same time on unknown usernames as on wrong passwords.
_DUMMY_HASH = bcrypt.hashpw(b"not-a-real-password", bcrypt.gensalt(4))


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(get_settings().bcrypt_rounds)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("ascii")


def verify_password(password: str, password_hash: str | None) -> bool:
    if password_hash is None:
        bcrypt.checkpw(b"x", _DUMMY_HASH)
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except ValueError:
        return False


def create_access_token(user_id: int, role: str) -> tuple[str, datetime]:
    settings = get_settings()
    now = utcnow()
    expires_at = now + timedelta(minutes=settings.access_token_minutes)
    payload = {"sub": str(user_id), "role": role, "iat": now, "exp": expires_at}
    token = jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)
    return token, expires_at


def decode_access_token(token: str) -> int:
    """Return the user id inside a valid token. Raises jwt.PyJWTError otherwise."""
    payload = jwt.decode(token, get_settings().secret_key, algorithms=[ALGORITHM])
    return int(payload["sub"])
