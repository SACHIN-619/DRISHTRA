"""
DRISHTRA System Health and Operational Status Endpoint
"""
from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(tags=["Health & Status"])

@router.get("/health")
def health_check():
    return {
        "status": "HEALTHY",
        "system": settings.PROJECT_NAME,
        "subtitle": settings.PROJECT_SUBTITLE,
        "version": settings.PROJECT_VERSION,
        "environment": settings.ENVIRONMENT,
        "air_gapped_mode": settings.IS_AIR_GAPPED
    }
