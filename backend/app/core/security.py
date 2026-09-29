from datetime import datetime, timedelta, timezone
from functools import lru_cache
import secrets

import jwt
from pwdlib import PasswordHash

from app.core.config import Settings

password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hasher.verify(plain_password, hashed_password)


@lru_cache
def dummy_password_hash() -> str:
    # Unknown accounts still perform an Argon2 verification.
    return hash_password(secrets.token_urlsafe(32))


def create_access_token(user_id: int, settings: Settings) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": str(user_id), "iat": now,
         "exp": now + timedelta(minutes=settings.access_token_expire_minutes)},
        settings.jwt_secret_key.get_secret_value(), algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str, settings: Settings) -> int:
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key.get_secret_value(), algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "iat", "exp"]},
        )
    except (TypeError, ValueError, OverflowError) as error:
        raise jwt.InvalidTokenError("Invalid claims") from error
    subject = payload["sub"]
    if not isinstance(subject, str) or not subject.isascii() or not subject.isdecimal():
        raise jwt.InvalidTokenError("Invalid subject")
    if len(subject) > 10 or not 0 < int(subject) <= 2_147_483_647:
        raise jwt.InvalidTokenError("Invalid subject")
    return int(subject)
