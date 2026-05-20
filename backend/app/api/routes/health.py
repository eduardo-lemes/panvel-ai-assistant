from fastapi import APIRouter

from app.application.services.health import build_health_status
from app.domain.models.health import HealthResponse
from app.infrastructure.config.settings import get_settings


router = APIRouter()


@router.get("/health", response_model=HealthResponse, summary="Health check")
def health_check() -> HealthResponse:
    settings = get_settings()
    return build_health_status(settings)
