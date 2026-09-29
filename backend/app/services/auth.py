from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import dummy_password_hash, hash_password, verify_password
from app.models import User
from app.schemas.user import UserCreate


class DuplicateEmailError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


def find_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.strip().lower()))


def create_user(db: Session, payload: UserCreate) -> User:
    if find_user_by_email(db, str(payload.email)) is not None:
        raise DuplicateEmailError
    user = User(
        first_name=payload.first_name, last_name=payload.last_name, email=str(payload.email),
        hashed_password=hash_password(payload.password.get_secret_value()),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # Resolve duplicate-email races without masking unrelated integrity errors.
        if find_user_by_email(db, str(payload.email)) is not None:
            raise DuplicateEmailError from None
        raise
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    user = find_user_by_email(db, email)
    valid = verify_password(password, user.hashed_password if user else dummy_password_hash())
    if not valid or user is None or not user.is_active:
        raise InvalidCredentialsError
    return user
