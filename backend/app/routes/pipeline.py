from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
import shutil
import tempfile
import os
import uuid

# OCR modules
from app.ocr import (
    aadhaar_wrapper,
    passport_wrapper,
    visa_wrapper,
    driving_license_wrapper,
    national_id_wrapper,
    permit_wrapper
)

# Validation engine
from app.module2_validation.core.validator import ValidationEngine
from app.module2_validation.schemas.input import DocumentInput

router = APIRouter()
validator = ValidationEngine()

@router.post("/process-document")
async def process_document(
    document_type: str = Form(...),
    file: UploadFile = File(...)
):
    valid_types = ["AADHAAR", "PASSPORT", "VISA", "DRIVING_LICENSE", "NATIONAL_ID", "PERMIT"]
    doc_type_upper = document_type.upper()
    
    if doc_type_upper not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid document_type. Must be one of {valid_types}")

    # 1. Save uploaded file temporarily
    temp_dir = tempfile.mkdtemp()
    temp_file_path = os.path.join(temp_dir, file.filename)
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 2. Run corresponding OCR wrapper
        if doc_type_upper == "AADHAAR":
            ocr_res = aadhaar_wrapper.process(temp_file_path)
        elif doc_type_upper == "PASSPORT":
            ocr_res = passport_wrapper.process(temp_file_path)
        elif doc_type_upper == "VISA":
            ocr_res = visa_wrapper.process(temp_file_path)
        elif doc_type_upper == "DRIVING_LICENSE":
            ocr_res = driving_license_wrapper.process(temp_file_path)
        elif doc_type_upper == "NATIONAL_ID":
            ocr_res = national_id_wrapper.process(temp_file_path)
        elif doc_type_upper == "PERMIT":
            ocr_res = permit_wrapper.process(temp_file_path)
            
        # 3. Construct DocumentInput for Validation
        # The OCR result gives us fields
        fields = ocr_res.get("fields", {})
        ocr_confidence = ocr_res.get("ocr_confidence", 0.0)
        
        doc_input = DocumentInput(
            request_id=str(uuid.uuid4()),
            document_type=doc_type_upper,
            fields=fields,
            ocr_confidence=ocr_confidence
        )
        
        # 4. Run Module 2 Validation
        validation_result = validator.validate_document(doc_input)
        
        # 5. Return combined results
        return {
            "ocr_result": ocr_res,
            "validation_result": validation_result.model_dump()
        }
        
    finally:
        # Clean up
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        os.rmdir(temp_dir)
