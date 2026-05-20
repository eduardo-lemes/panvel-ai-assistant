from fastapi import FastAPI

from app.api.router import api_router
from app.infrastructure.config.settings import get_settings
from app.observability.logging import configure_logging


settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
)
app.include_router(api_router)
