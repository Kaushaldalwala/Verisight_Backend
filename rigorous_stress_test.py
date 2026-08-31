"""
rigorous_stress_test.py — Expert QA Stress Test Suite for VeriSight

Simulates adversarial inputs, boundary conditions, malformed data, unicode injection,
SQL injection attempts, unparseable dates, missing fields, zero confidence, and unknown document types.
"""

import sys
import unittest
import tempfile
import os
from pathlib import Path

backend_path = Path(__file__).resolve().parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.module2_validation.core.validator import ValidationEngine
from app.module2_validation.core.normalization import FieldNormalizer
from app.module2_validation.database.seed import seed_all
from app.module2_validation.schemas.input import DocumentInput
from app.module2_validation.schemas.common import ValidationStatus, DocumentStatus
from app.ocr.adapter import OCROutputAdapter


class ExpertQASressTestSuite(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls.db_path = cls.tmp_file.name
        cls.tmp_file.close()

        seed_all(db_path=cls.db_path, passports=50, visas=50, aadhaars=50, licenses=50, ids=50, permits=50, seed_val=123)
        cls.engine = ValidationEngine(db_path=cls.db_path)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.db_path):
            try:
                os.remove(cls.db_path)
            except OSError:
                pass

    def test_sql_injection_attempt(self):
        """Verify parameterized queries block SQL injection attempts safely."""
        sql_payload = "P0000001' OR '1'='1'; DROP TABLE passports; --"
        doc_input = DocumentInput(
            document_type="passport",
            fields={"passport_number": sql_payload, "name": "HACKER"}
        )
        result = self.engine.validate_document(doc_input)
        # Should not crash, and should return NO match or handle cleanly
        self.assertIsNotNone(result)
        self.assertFalse(result.database_match)

    def test_malformed_unparseable_dates(self):
        """Verify unparseable or nonsense dates do not crash the engine."""
        bad_dates = ["INVALID_DATE", "99999-999-999", "00/00/0000", "2023-02-31", "", None]
        for b_date in bad_dates:
            doc_input = DocumentInput(
                document_type="passport",
                fields={
                    "passport_number": "P0000001",
                    "name": "DAVID GUPTA",
                    "date_of_birth": b_date
                }
            )
            result = self.engine.validate_document(doc_input)
            self.assertIsNotNone(result)

    def test_unknown_document_type(self):
        """Verify engine falls back cleanly for unknown document types."""
        doc_input = DocumentInput(
            document_type="intergalactic_space_permit",
            fields={"permit_number": "SP-999", "name": "ALIEN"}
        )
        result = self.engine.validate_document(doc_input)
        self.assertIsNotNone(result)
        self.assertEqual(result.document_type, "intergalactic_space_permit")

    def test_empty_and_null_fields(self):
        """Verify empty dict, None fields, or empty values handle cleanly."""
        doc_input = DocumentInput(
            document_type="passport",
            fields={"passport_number": None, "name": "", "nationality": None}
        )
        result = self.engine.validate_document(doc_input)
        self.assertIsNotNone(result)
        self.assertEqual(result.validation_status, ValidationStatus.FAIL)

    def test_unicode_and_special_character_injection(self):
        """Verify unicode, special characters, and HTML tags do not cause exceptions."""
        weird_name = "<script>alert('xss')</script> Jöhn Døe €500 \x00"
        doc_input = DocumentInput(
            document_type="passport",
            fields={"passport_number": "P0000001", "name": weird_name}
        )
        result = self.engine.validate_document(doc_input)
        self.assertIsNotNone(result)

    def test_score_clamping(self):
        """Verify validation score is strictly clamped between 0.0 and 100.0."""
        # Force compounding errors
        doc_input = DocumentInput(
            document_type="passport",
            ocr_confidence=0.0,
            fields={
                "passport_number": "INVALID!!!",
                "name": "WRONG NAME",
                "date_of_birth": "2099-01-01",
                "date_of_expiry": "1900-01-01"
            }
        )
        result = self.engine.validate_document(doc_input)
        self.assertGreaterEqual(result.validation_score, 0.0)
        self.assertLessEqual(result.validation_score, 100.0)

    def test_adapter_resilience_to_malformed_ocr(self):
        """Verify OCROutputAdapter handles completely empty or corrupted input dicts."""
        malformed_inputs = [
            {},
            {"document_type": None},
            {"fields": None},
            {"fields": "not_a_dict"},
            {"ocr_confidence": "invalid_float"}
        ]
        for m_input in malformed_inputs:
            try:
                adapted = OCROutputAdapter.adapt(m_input)
                self.assertIsNotNone(adapted)
                self.assertIn("document_type", adapted)
                self.assertIn("fields", adapted)
            except Exception as e:
                self.fail(f"OCROutputAdapter crashed on malformed input {m_input}: {e}")


if __name__ == "__main__":
    unittest.main()
