from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User

DatabaseSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]
bearer = HTTPBearer(auto_error=False)


def unauthorized() -> HTTPException:
    return HTTPException(status_code=401, detail="Could not validate credentials",
                         headers={"WWW-Authenticate": "Bearer"})


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: DatabaseSession, settings: AppSettings,
) -> User:
    if credentials is None:
        raise unauthorized()
    try:
        user_id = decode_access_token(credentials.credentials, settings)
    except jwt.InvalidTokenError:
        raise unauthorized() from None
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise unauthorized()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
