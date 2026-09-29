from datetime import datetime, timedelta, timezone

import jwt
import pytest
from sqlalchemy import select

from app.core.security import create_access_token, verify_password
from app.models import User

AUTH = "/api/v1/auth"
PAYLOAD = {"first_name": " Sara ", "last_name": " Demo ", "email": " Sara.Demo@Example.com ",
           "password": "Fake-test-password-123!"}
PUBLIC_FIELDS = {"id", "first_name", "last_name", "email", "is_active", "created_at", "updated_at"}


@pytest.fixture
def registered(client):
    response = client.post(f"{AUTH}/register", json=PAYLOAD)
    assert response.status_code == 201
    return response.json()


def credentials(**changes):
    return {"email": "sara.demo@example.com", "password": PAYLOAD["password"]} | changes


def test_registration_normalizes_and_hashes(client, registered, db_session):
    assert set(registered) == PUBLIC_FIELDS
    assert registered["first_name"] == "Sara"
    assert registered["last_name"] == "Demo"
    assert registered["email"] == "sara.demo@example.com"
    assert registered["is_active"] is True
    user = db_session.get(User, registered["id"])
    assert user.hashed_password != PAYLOAD["password"]
    assert user.hashed_password.startswith("$argon2id$")
    assert verify_password(PAYLOAD["password"], user.hashed_password)
    assert user.created_at and user.updated_at


def test_duplicate_registration(client, registered):
    response = client.post(f"{AUTH}/register", json=PAYLOAD | {"email": "SARA.DEMO@example.com"})
    assert response.status_code == 409
    assert PAYLOAD["password"] not in response.text


@pytest.mark.parametrize("changes", [{"email": "invalid"}, {"password": "Tiny7"},
    {"password": "a" * 129}, {"first_name": " "}, {"last_name": "x" * 101},
    {"role": "admin"}, {"is_active": False}, {"hashed_password": "injected"}])
def test_invalid_registration(client, changes):
    payload = PAYLOAD | changes
    response = client.post(f"{AUTH}/register", json=payload)
    assert response.status_code == 422
    assert payload["password"] not in response.text
    assert all("input" not in error and "ctx" not in error for error in response.json()["detail"])


def test_valid_login_and_me(client, registered, settings):
    response = client.post(f"{AUTH}/login", json=credentials(email=" SARA.DEMO@example.com "))
    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"access_token", "token_type"}
    assert data["token_type"] == "bearer"
    claims = jwt.decode(data["access_token"], settings.jwt_secret_key.get_secret_value(), algorithms=["HS256"])
    assert claims["sub"] == str(registered["id"])
    assert claims["exp"] - claims["iat"] == 30 * 60
    response = client.get(f"{AUTH}/me", headers={"Authorization": f"Bearer {data['access_token']}"})
    assert response.status_code == 200
    assert response.json() == registered
    assert set(response.json()) == PUBLIC_FIELDS


def test_login_failures_are_generic(client, registered, db_session):
    wrong = client.post(f"{AUTH}/login", json=credentials(password="wrong"))
    unknown = client.post(f"{AUTH}/login", json=credentials(email="unknown@example.com"))
    user = db_session.get(User, registered["id"])
    user.is_active = False
    db_session.commit()
    inactive = client.post(f"{AUTH}/login", json=credentials())
    for response in (wrong, unknown, inactive):
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"
        assert response.json() == {"detail": "Could not validate credentials"}


@pytest.mark.parametrize("header", [None, "Bearer", "Bearer not.a.token", "Basic abc"])
def test_missing_or_malformed_bearer(client, header):
    response = client.get(f"{AUTH}/me", headers={"Authorization": header} if header else {})
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("state", ["expired", "deleted", "inactive", "unknown", "wrong-secret"])
def test_unusable_tokens(client, registered, db_session, settings, state):
    token = create_access_token(registered["id"], settings)
    user = db_session.get(User, registered["id"])
    if state == "deleted":
        db_session.delete(user)
        db_session.commit()
    elif state == "inactive":
        user.is_active = False
        db_session.commit()
    elif state == "unknown":
        token = create_access_token(999999, settings)
    elif state in {"expired", "wrong-secret"}:
        now = datetime.now(timezone.utc)
        token = jwt.encode({"sub": str(user.id), "iat": now - timedelta(hours=2),
                            "exp": now - timedelta(hours=1) if state == "expired" else now + timedelta(hours=1)},
                           "different-test-only-secret-123456789" if state == "wrong-secret" else
                           settings.jwt_secret_key.get_secret_value(), algorithm="HS256")
    response = client.get(f"{AUTH}/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Could not validate credentials"}


def test_password_whitespace_is_not_trimmed(client):
    password = "  Fake-test-password-123!  "
    assert client.post(f"{AUTH}/register", json=PAYLOAD | {"password": password}).status_code == 201
    assert client.post(f"{AUTH}/login", json=credentials(password=password)).status_code == 200
    assert client.post(f"{AUTH}/login", json=credentials(password=password.strip())).status_code == 401


def test_duplicate_race_rolls_back(client, registered, db_session, monkeypatch):
    from app.services import auth
    from app.schemas.user import UserCreate
    real_find = auth.find_user_by_email
    calls = 0
    def miss_once(db, email):
        nonlocal calls
        calls += 1
        return None if calls == 1 else real_find(db, email)
    monkeypatch.setattr(auth, "find_user_by_email", miss_once)
    with pytest.raises(auth.DuplicateEmailError):
        auth.create_user(db_session, UserCreate(**PAYLOAD))
    assert len(list(db_session.scalars(select(User)))) == 1
