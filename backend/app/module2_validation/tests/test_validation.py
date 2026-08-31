"""
test_validation.py

Comprehensive unit & integration test suite for VeriSight Module 2.
Uses standard library unittest for execution without external test dependencies.
"""

import os
import unittest
import tempfile

from app.module2_validation.config.settings import DocumentConfigLoader
from app.module2_validation.core.normalization import FieldNormalizer
from app.module2_validation.core.validator import ValidationEngine
from app.module2_validation.database.seed import seed_all
from app.module2_validation.database.repository import DocumentRepository
from app.module2_validation.providers.synthetic import SyntheticProvider
from app.module2_validation.providers.government import GovernmentProvider
from app.module2_validation.schemas.input import DocumentInput
from app.module2_validation.schemas.common import ValidationStatus
from app.ocr.adapter import OCROutputAdapter


class TestModule2Validation(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls.db_path = cls.tmp_file.name
        cls.tmp_file.close()

        seed_all(
            db_path=cls.db_path,
            passports=100,
            visas=100,
            aadhaars=100,
            licenses=100,
            ids=100,
            permits=100,
            seed_val=42
        )

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.db_path):
            try:
                os.remove(cls.db_path)
            except OSError:
                pass

    def test_normalization(self):
        self.assertEqual(FieldNormalizer.normalize_name("Arjun  Mehta<"), "ARJUN MEHTA")
        self.assertEqual(FieldNormalizer.normalize_identifier("P-123 456"), "P123456")
        self.assertEqual(FieldNormalizer.normalize_numeric_identifier("O123L5S"), "0123155")
        self.assertEqual(FieldNormalizer.normalize_date("1998/04/12"), "1998-04-12")
        self.assertEqual(FieldNormalizer.normalize_gender("Male"), "M")

        matched, ratio = FieldNormalizer.fuzzy_match_names("ARJUN MEHTA", "ARJUN MEHTA")
        self.assertTrue(matched)
        self.assertEqual(ratio, 100.0)

    def test_yaml_config_loader(self):
        config = DocumentConfigLoader.load_config("passport")
        self.assertEqual(config["document_type"], "passport")
        self.assertIn("passport_number", config["fields"])
        self.assertTrue(config["fields"]["passport_number"]["required"])

    def test_synthetic_provider(self):
        provider = SyntheticProvider(self.db_path)
        rec, source, status = provider.find_document("passport", "P0000001")
        self.assertIsNotNone(rec)
        self.assertEqual(rec["passport_number"], "P0000001")
        self.assertEqual(source, "synthetic_database")

    def test_government_provider(self):
        provider = GovernmentProvider()
        rec, source, status = provider.find_document("passport", "P0000001")
        self.assertIsNone(rec)
        self.assertTrue("unauthorized" in status or "unconfigured" in status or "connection" in status)

    def test_valid_passport_validation(self):
        engine = ValidationEngine(db_path=self.db_path)

        repo = DocumentRepository(self.db_path)
        rec = repo.find_by_identifier("passport", "P0000001")
        self.assertIsNotNone(rec)

        doc_input = DocumentInput(
            document_type="passport",
            fields={
                "passport_number": rec["passport_number"],
                "name": rec["name"],
                "nationality": rec["nationality"],
                "date_of_birth": rec["date_of_birth"],
                "date_of_expiry": rec["date_of_expiry"],
                "gender": rec["gender"]
            }
        )

        result = engine.validate_document(doc_input)
        self.assertTrue(result.database_match)
        self.assertGreaterEqual(result.validation_score, 80.0)

    def test_missing_required_field_validation(self):
        engine = ValidationEngine(db_path=self.db_path)
        doc_input = DocumentInput(
            document_type="passport",
            fields={
                "name": "TEST USER"
            }
        )
        result = engine.validate_document(doc_input)
        self.assertFalse(result.database_match)
        self.assertLess(result.validation_score, 80.0)
        self.assertGreater(len(result.mismatches), 0)

    def test_future_dob_validation(self):
        engine = ValidationEngine(db_path=self.db_path)
        doc_input = DocumentInput(
            document_type="passport",
            fields={
                "passport_number": "P0000001",
                "name": "ARJUN MEHTA",
                "nationality": "IND",
                "date_of_birth": "2099-01-01",
                "date_of_expiry": "2033-01-01",
                "gender": "M"
            }
        )
        result = engine.validate_document(doc_input)
        mismatch_types = [m.type for m in result.mismatches]
        self.assertIn("FUTURE_DOB", mismatch_types)

    def test_ocr_output_adapter(self):
        raw_ocr = {
            "document_type": "PASSPORT",
            "status": "OCR SUCCESS",
            "ocr_confidence": 94.5,
            "fields": {
                "name": "ARJUN",
                "surname": "MEHTA",
                "passport_number": "P0000001",
                "nationality": "IND",
                "date_of_birth": "1998-04-12",
                "expiration_date": "2033-04-11",
                "sex": "M"
            }
        }
        adapted = OCROutputAdapter.adapt(raw_ocr)
        self.assertEqual(adapted["document_type"], "passport")
        self.assertEqual(adapted["ocr_confidence"], 94.5)
        self.assertEqual(adapted["fields"]["passport_number"], "P0000001")
        self.assertEqual(adapted["fields"]["date_of_expiry"], "2033-04-11")
        self.assertEqual(adapted["fields"]["name"], "ARJUN MEHTA")


if __name__ == "__main__":
    unittest.main()
