"""
routes.py

FastAPI router for Module 2 Document Validation endpoints.
Provides POST /api/v1/validate and GET /api/v1/supported-types.
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.auth import get_current_user
from app.module2_validation.schemas.input import DocumentInput
from app.module2_validation.schemas.output import ValidationResult
from app.module2_validation.services.validation_service import ValidationService
from app.module2_validation.config.settings import DocumentConfigLoader

router = APIRouter()
service = ValidationService()


@router.post(
    "/validate",
    response_model=ValidationResult,
    summary="Validate document fields against rules and reference databases",
)
async def validate_document(
    payload: DocumentInput,
    current_user=Depends(get_current_user),
):
    """
    Accepts standardized document input or OCR output and runs comprehensive
    Module 2 validation checks (format, types, dates, database lookup, status, scoring).
    """
    if not payload.document_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Required document_type field is missing.",
        )

    return service.validator.validate_document(payload)


@router.get(
    "/supported-types",
    summary="Get list of dynamically supported document types",
)
async def get_supported_types():
    """
    Returns list of document types supported by configuration.
    """
    return {
        "supported_types": DocumentConfigLoader.get_supported_types()
    }
