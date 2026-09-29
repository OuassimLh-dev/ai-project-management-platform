from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.core.security import create_access_token, decode_access_token, hash_password, verify_password


def test_argon2_hashing():
    password = "Fake-password-for-tests-123!"
    first, second = hash_password(password), hash_password(password)
    assert first.startswith("$argon2id$")
    assert first != password and first != second
    assert verify_password(password, first)
    assert not verify_password("wrong", first)


def test_valid_jwt(settings):
    assert decode_access_token(create_access_token(123, settings), settings) == 123


@pytest.mark.parametrize("subject", ["0", "-1", "2147483648", "1" * 100, "abc", "١", 1, None])
def test_reject_invalid_subject(settings, subject):
    now = datetime.now(timezone.utc)
    token = jwt.encode({"sub": subject, "iat": now, "exp": now + timedelta(minutes=1)},
                       settings.jwt_secret_key.get_secret_value(), algorithm="HS256")
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token, settings)


@pytest.mark.parametrize("missing", ["sub", "iat", "exp"])
def test_required_claims(settings, missing):
    now = datetime.now(timezone.utc)
    claims = {"sub": "1", "iat": now, "exp": now + timedelta(minutes=1)}
    del claims[missing]
    token = jwt.encode(claims, settings.jwt_secret_key.get_secret_value(), algorithm="HS256")
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token, settings)


def test_expired_token(settings):
    now = datetime.now(timezone.utc)
    token = jwt.encode({"sub": "1", "iat": now - timedelta(hours=1), "exp": now - timedelta(seconds=1)},
                       settings.jwt_secret_key.get_secret_value(), algorithm="HS256")
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token, settings)


def test_unsigned_token_rejected(settings):
    now = datetime.now(timezone.utc)
    token = jwt.encode({"sub": "1", "iat": now, "exp": now + timedelta(minutes=1)}, key="", algorithm="none")
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token, settings)


@pytest.mark.parametrize("claim,value", [("exp", []), ("iat", []), ("exp", "invalid"),
                                         ("iat", "invalid"), ("exp", float("inf"))])
def test_malformed_numeric_claims(settings, claim, value):
    now = datetime.now(timezone.utc)
    claims = {"sub": "1", "iat": now, "exp": now + timedelta(minutes=1)}
    claims[claim] = value
    token = jwt.encode(claims, settings.jwt_secret_key.get_secret_value(), algorithm="HS256")
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token, settings)
