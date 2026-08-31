from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.auth import router as auth_router
from app.routes.ocr import router as ocr_router
from app.routes.pipeline import router as pipeline_router
from app.module2_validation.api.routes import router as validation_router
from fastapi.staticfiles import StaticFiles

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("verisight")

app = FastAPI(
    title="VeriSight API",
    description=(
        "Document OCR & verification backend. "
        "Supports Passport, Aadhaar, Visa, Driving License, National ID, and Permit."
    ),
    version="1.0.0",
)

# ----------------------------------------------------------------
# CORS — allow all origins in development.
# Restrict origins in production by listing specific frontend URLs.
# ----------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------------------------------------
# Routers
# ----------------------------------------------------------------
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(ocr_router,  prefix="/ocr",  tags=["OCR"])
app.include_router(pipeline_router, prefix="/api/v1", tags=["Pipeline"])
app.include_router(validation_router, prefix="/api/v1/validation", tags=["Validation"])


# ----------------------------------------------------------------
# Health check
# ----------------------------------------------------------------
@app.get("/", tags=["Health"])
def root():
    return {"message": "VeriSight backend is running!"}


# ----------------------------------------------------------------
# Supabase connectivity test
# ----------------------------------------------------------------
@app.get("/test-supabase", tags=["Health"])
def test_supabase():
    from app.services.supabase import supabase
    response = supabase.table("officer_profiles").select("*").limit(1).execute()
    return {
        "connected": True,
        "rows_returned": len(response.data),
    }
