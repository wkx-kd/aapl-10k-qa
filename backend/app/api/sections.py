"""Section metadata API endpoints."""

import logging

from fastapi import APIRouter, Request

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/sections")
async def get_sections(request: Request):
    """Get available years and section types."""
    from app.services.data_loader import load_records, get_available_years, get_section_types
    from app.config import get_settings

    settings = get_settings()
    records = load_records(settings.data_path)

    return {
        "years": get_available_years(records),
        "sections": get_section_types(records),
    }
