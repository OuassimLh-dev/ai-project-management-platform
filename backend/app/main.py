from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.core.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings if settings is not None else get_settings()
    application = FastAPI(title=f"{settings.app_name} API")
    application.dependency_overrides[get_settings] = lambda: settings
    application.include_router(health_router, prefix=settings.api_v1_prefix)
    return application


app = create_app()
