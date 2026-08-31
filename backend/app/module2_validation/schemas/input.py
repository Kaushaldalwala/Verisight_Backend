"""
input.py

Input schemas for Module 2 Document Validation.
"""

import uuid
from typing import Any, Optional
from pydantic import BaseModel, Field


class DocumentInput(BaseModel):
    """
    Standardized document input schema for validation engine.
    Accepts raw fields or output from Module 1 adapter.
    """
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_type: str = Field(..., description="Document type e.g. passport, visa, aadhaar, driving_license, national_id, permit")
    document_country: Optional[str] = Field(None, description="ISO country code e.g. IN, US")
    ocr_confidence: float = Field(0.0, ge=0.0, le=100.0, description="OCR confidence percentage 0-100")
    fields: dict[str, Any] = Field(default_factory=dict, description="Extracted key-value document fields")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Optional request metadata")
