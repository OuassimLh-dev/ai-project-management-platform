from fastapi import APIRouter, HTTPException

from app.api.dependencies import AppSettings, CurrentUser, DatabaseSession, unauthorized
from app.core.security import create_access_token
from app.models import User
from app.schemas.user import LoginRequest, TokenResponse, UserCreate, UserRead
from app.services import auth as service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=201)
def register(payload: UserCreate, db: DatabaseSession) -> User:
    try:
        return service.create_user(db, payload)
    except service.DuplicateEmailError:
        raise HTTPException(status_code=409, detail="Email already registered") from None


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: DatabaseSession, settings: AppSettings) -> TokenResponse:
    try:
        user = service.authenticate_user(db, str(payload.email), payload.password.get_secret_value())
    except service.InvalidCredentialsError:
        raise unauthorized() from None
    return TokenResponse(access_token=create_access_token(user.id, settings))


@router.get("/me", response_model=UserRead)
def me(user: CurrentUser) -> User:
    return user
