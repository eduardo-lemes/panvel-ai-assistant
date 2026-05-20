from app.domain.models.health import HealthResponse
from app.infrastructure.config.settings import Settings


def build_health_status(settings: Settings) -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )
