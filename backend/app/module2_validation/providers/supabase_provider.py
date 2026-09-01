import os
from typing import Any, Optional
from app.module2_validation.schemas.common import DataSource
from app.module2_validation.providers.base import DocumentDataProvider
from app.services.supabase import supabase_admin as supabase  # use service role to bypass RLS on val_* tables

class SupabaseProvider(DocumentDataProvider):
    source_type = DataSource.GOVERNMENT_API  # We treat this as the source of truth

    def _get_table_info(self, document_type: str) -> tuple[str, str]:
        doc_type = document_type.upper()
        if doc_type == "AADHAAR":
            return "val_aadhar_details", "aadhaar_number"
        elif doc_type == "PASSPORT":
            return "val_passport_details", "passport_number"
        elif doc_type == "VISA":
            return "val_visa_details", "visa_number"
        elif doc_type == "DRIVING_LICENSE":
            return "val_driving_license_details", "license_number"
        elif doc_type == "NATIONAL_ID":
            return "val_national_id_details", "id_number"
        elif doc_type == "PERMIT":
            return "val_permit_details", "permit_number"
        else:
            raise ValueError(f"Unsupported document type for Supabase provider: {document_type}")

    def find_document(self, document_type: str, identifier: str) -> tuple[Optional[dict[str, Any]], DataSource, str]:
        try:
            table_name, id_col = self._get_table_info(document_type)
            
            response = supabase.table(table_name).select("*").eq(id_col, identifier).limit(1).execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0], self.source_type, "active"
            else:
                return None, self.source_type, "not_found"
                
        except Exception as e:
            # Fallback or log error
            return None, self.source_type, f"error: {str(e)}"
