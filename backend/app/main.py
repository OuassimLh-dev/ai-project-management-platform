from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routes.auth import router as auth_router
from app.api.routes.teams import router as teams_router
from app.services.team_authorization import TeamError

from app.api.routes.health import router as health_router
from app.core.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings if settings is not None else get_settings()
    application = FastAPI(title=f"{settings.app_name} API")
    application.dependency_overrides[get_settings] = lambda: settings
    application.include_router(health_router, prefix=settings.api_v1_prefix)
    application.include_router(auth_router, prefix=settings.api_v1_prefix)

    application.include_router(teams_router, prefix=settings.api_v1_prefix)

    @application.exception_handler(TeamError)
    async def team_error(request: Request, exc: TeamError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @application.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Validation responses must not echo submitted passwords or other inputs.
        errors = [{key: error[key] for key in ("type", "loc", "msg")} for error in exc.errors()]
        status = 400 if any(error["type"] == "owner_assignment" for error in errors) else 422
        return JSONResponse(status_code=status, content={"detail": errors})

    return application


app = create_app()
