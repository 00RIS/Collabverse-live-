"""
app/core/security.py

WHAT THIS FILE IS:
All password-hashing and JWT (JSON Web Token) logic lives here, in one
place, so no other file ever touches raw passwords or signs tokens on
its own.

WHY IT EXISTS:
- Passwords must NEVER be stored in plain text. We store a one-way bcrypt
  hash. Even if the database leaks, an attacker cannot recover the
  original password from the hash.
- JWTs are how the API recognizes a logged-in user on every request
  without needing a server-side session store. The token is a signed
  piece of JSON the client sends back on every request (in the
  Authorization header). Because it's signed with SECRET_KEY, the server
  can trust its contents without hitting the database every time.

TWO TOKEN TYPES:
- Access token: short-lived (e.g. 30 min). Sent with every API request.
- Refresh token: long-lived (e.g. 7 days). Used only to obtain a new
  access token when the old one expires, without forcing the user to
  log in again. This split limits the damage if an access token leaks
  (it expires quickly) while still keeping the user logged in.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# CryptContext handles the bcrypt algorithm details for us (salt
# generation, work factor, etc.) so we never implement hashing ourselves.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Turn a plain-text password into an irreversible bcrypt hash."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a login attempt's password against the stored hash."""
    return pwd_context.verify(plain_password, hashed_password)


def _create_token(subject: str, expires_delta: timedelta, token_type: str) -> str:
    """
    Build and sign a JWT.

    `subject` is normally the user's ID. `token_type` ("access" or
    "refresh") is embedded in the payload so that, when we later decode
    a token, we can reject a refresh token that's being used as an
    access token (or vice versa).
    """
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "type": token_type,
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(user_id: str) -> str:
    return _create_token(
        subject=user_id,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        token_type="access",
    )


def create_refresh_token(user_id: str) -> str:
    return _create_token(
        subject=user_id,
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        token_type="refresh",
    )


def decode_token(token: str) -> dict[str, Any] | None:
    """
    Verify a token's signature and expiry, and return its payload.
    Returns None if the token is invalid, expired, or tampered with.
    """
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None
