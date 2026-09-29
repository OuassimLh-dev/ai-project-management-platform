from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password
from app.models import User


def make_user(email=" sara@example.com "):
    return User(first_name="Sara", last_name="Demo", email=email,
                hashed_password=hash_password("Fake-test-password-123!"))


def test_user_defaults_timestamps_and_normalization(db_session):
    user = make_user(" SARA@Example.com ")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    assert user.id > 0
    assert user.email == "sara@example.com"
    assert user.is_active is True
    assert user.created_at and user.updated_at
    created = user.created_at
    user.updated_at = datetime(2000, 1, 1, tzinfo=timezone.utc)
    db_session.commit()
    user.first_name = "Sarah"
    db_session.commit()
    db_session.refresh(user)
    assert user.updated_at.year > 2000
    assert user.created_at == created


def test_unique_email_enforced_by_database(db_session):
    db_session.add(make_user())
    db_session.commit()
    db_session.add(make_user("SARA@example.com"))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
