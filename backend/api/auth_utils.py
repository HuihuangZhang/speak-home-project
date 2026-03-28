from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt, ExpiredSignatureError, JWTError  # noqa: F401 (re-exported for callers)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(user_id: int, secret: str, expire_hours: int = 24) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(hours=expire_hours)
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": now,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_access_token(token: str, secret: str) -> dict:
    # Raises ExpiredSignatureError or JWTError on invalid token
    return jwt.decode(token, secret, algorithms=["HS256"])
