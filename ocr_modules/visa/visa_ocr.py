
# """
# visa_ocr.py
# Modular Visa OCR + MRZ consistency verification.

# NOTE:
# This module performs OCR and internal consistency checks.
# "VERIFIED" means the extracted visual fields are consistent
# with the detected MRZ; it does not prove government issuance/authenticity.
# """



# """The threshold is set to 0.50 for better results and 0.75 we are gettimg too much low prediciton almost requires crystal clear experience"""
# import re
# from difflib import SequenceMatcher
# from pathlib import Path

# import cv2
# import easyocr


# class VisaOCR:
#     def __init__(self, languages=None, gpu=False):
#         self.reader = easyocr.Reader(languages or ["en"], gpu=gpu)

#     @staticmethod
#     def _center(bbox):
#         return (
#             sum(p[0] for p in bbox) / 4,
#             sum(p[1] for p in bbox) / 4,
#         )

#     @staticmethod
#     def _normalize(value):
#         if not value:
#             return ""
#         return re.sub(r"[^A-Z0-9]", "", str(value).upper())

#     @staticmethod
#     def _normalize_name(value):
#         if not value:
#             return ""
#         value = str(value).upper().replace("<", " ")
#         value = re.sub(r"[^A-Z ]", "", value)
#         return re.sub(r"\s+", " ", value).strip()

#     @staticmethod
#     def _clean_mrz(text):
#         text = text.upper().replace(" ", "")
#         replacements = {"«": "<", "‹": "<", "_": "<", "—": "<"}
#         for old, new in replacements.items():
#             text = text.replace(old, new)
#         return text

#     def load_image(self, image_path):
#         path = Path(image_path)
#         if not path.exists():
#             raise FileNotFoundError(f"Visa image not found: {path}")

#         image = cv2.imread(str(path))
#         if image is None:
#             raise ValueError(f"Could not decode image: {path}")
#         return image

#     def preprocess(self, image):
#         gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
#         gray = cv2.GaussianBlur(gray, (3, 3), 0)
#         return cv2.adaptiveThreshold(
#             gray, 255,
#             cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
#             cv2.THRESH_BINARY,
#             31, 11
#         )

#     def ocr(self, image):
#         results = self.reader.readtext(
#             image, paragraph=False, detail=1
#         )
#         return [
#             {
#                 "text": text.strip(),
#                 "confidence": float(confidence),
#                 "bbox": bbox,
#             }
#             for bbox, text, confidence in results
#             if text.strip()
#         ]

#     def check_image_quality(self, ocr_data, threshold=0.50):
#         if not ocr_data:
#             return {
#                 "clear": False,
#                 "confidence": 0.0,
#                 "reason": "No text was detected."
#             }

#         avg = sum(x["confidence"] for x in ocr_data) / len(ocr_data)
#         readable = sum(x["confidence"] >= 0.50 for x in ocr_data)

#         if avg < threshold:
#             return {
#                 "clear": False,
#                 "confidence": avg,
#                 "reason": "OCR confidence is too low."
#             }

#         if readable < 3:
#             return {
#                 "clear": False,
#                 "confidence": avg,
#                 "reason": "Not enough readable text was detected."
#             }

#         return {
#             "clear": True,
#             "confidence": avg,
#             "reason": "Image quality is sufficient."
#         }

#     def find_value_after_label(self, ocr_data, labels, max_distance=250):
#         label_item = None

#         for item in ocr_data:
#             text = item["text"].lower()
#             if any(label.lower() in text for label in labels):
#                 label_item = item
#                 break

#         if label_item is None:
#             return None

#         lx, ly = self._center(label_item["bbox"])
#         candidates = []

#         for item in ocr_data:
#             if item is label_item or item["confidence"] < 0.30:
#                 continue

#             x, y = self._center(item["bbox"])
#             distance = abs(x - lx) + abs(y - ly)

#             if distance <= max_distance:
#                 candidates.append((distance, item))

#         if not candidates:
#             return None

#         candidates.sort(key=lambda x: x[0])
#         return candidates[0][1]["text"]

#     def extract_fields(self, ocr_data):
#         labels = {
#             "issuing_post": ["Issuing Post Name"],
#             "control_number": ["Control Number"],
#             "surname": ["Surname"],
#             "given_name": ["Given Name"],
#             "visa_type": ["Visa Type", "Visa Type /Class"],
#             "passport_number": ["Passport Number"],
#             "sex": ["Sex"],
#             "birth_date": ["Birth Date"],
#             "nationality": ["Nationality"],
#             "entries": ["Entries"],
#             "issue_date": ["Issue Date"],
#             "expiration_date": ["Expiration Date"],
#         }

#         return {
#             field: self.find_value_after_label(ocr_data, field_labels)
#             for field, field_labels in labels.items()
#         }

#     def extract_mrz(self, image):
#         h, w = image.shape[:2]
#         mrz_region = image[int(h * 0.65):h, 0:w]

#         results = self.reader.readtext(
#             mrz_region, paragraph=False, detail=1
#         )

#         lines = []
#         for bbox, text, confidence in results:
#             cleaned = self._clean_mrz(text)
#             if len(cleaned) >= 20:
#                 _, y = self._center(bbox)
#                 lines.append({
#                     "text": cleaned,
#                     "confidence": float(confidence),
#                     "y": y
#                 })

#         lines.sort(key=lambda x: x["y"])

#         if len(lines) < 2:
#             return {
#                 "valid": False,
#                 "reason": "Two MRZ lines were not detected."
#             }

#         line1 = lines[0]["text"].ljust(44, "<")[:44]
#         line2 = lines[1]["text"].ljust(44, "<")[:44]

#         name_parts = line1[5:44].split("<<", 1)
#         surname = name_parts[0].replace("<", " ").strip()
#         given_name = (
#             name_parts[1].replace("<", " ").strip()
#             if len(name_parts) > 1 else ""
#         )

#         return {
#             "valid": True,
#             "document_code": line1[0:2],
#             "issuing_country": line1[2:5],
#             "surname": surname,
#             "given_name": given_name,
#             "passport_number": line2[0:9].replace("<", ""),
#             "nationality": line2[10:13].replace("<", ""),
#             "birth_date": line2[13:19],
#             "sex": line2[20],
#             "expiration_date": line2[21:27],
#             "personal_number": line2[28:42].replace("<", ""),
#             "raw_line1": line1,
#             "raw_line2": line2,
#             "mrz_confidence": (
#                 (lines[0]["confidence"] + lines[1]["confidence"]) / 2
#             ),
#         }

#     def compare_field(self, visual, mrz, field):
#         if not visual or not mrz:
#             return {"status": "NOT_AVAILABLE", "similarity": 0.0}

#         if field in ("surname", "given_name"):
#             a = self._normalize_name(visual)
#             b = self._normalize_name(mrz)
#         else:
#             a = self._normalize(visual)
#             b = self._normalize(mrz)

#         similarity = SequenceMatcher(None, a, b).ratio()

#         if a == b:
#             status = "MATCH"
#         elif similarity >= 0.85:
#             status = "CLOSE_MATCH"
#         else:
#             status = "MISMATCH"

#         return {
#             "visual_value": visual,
#             "mrz_value": mrz,
#             "status": status,
#             "similarity": round(similarity, 3),
#         }

#     def verify(self, visa_data, mrz_data):
#         if not mrz_data.get("valid"):
#             return {
#                 "document_type": "VISA",
#                 "status": "CLEARER IMAGE REQUIRED",
#                 "reason": mrz_data.get(
#                     "reason", "MRZ could not be read reliably."
#                 ),
#             }

#         fields = [
#             "passport_number",
#             "surname",
#             "given_name",
#             "nationality",
#             "birth_date",
#             "sex",
#             "expiration_date",
#         ]

#         checks = {
#             field: self.compare_field(
#                 visa_data.get(field),
#                 mrz_data.get(field),
#                 field
#             )
#             for field in fields
#         }

#         available = [
#             x for x in checks.values()
#             if x["status"] != "NOT_AVAILABLE"
#         ]

#         if not available:
#             return {
#                 "document_type": "VISA",
#                 "status": "CLEARER IMAGE REQUIRED",
#                 "reason": "No reliable fields could be cross-validated.",
#                 "checks": checks,
#             }

#         score = sum(x["similarity"] for x in available) / len(available)
#         confidence = round(score * 100, 2)

#         matches = sum(x["status"] == "MATCH" for x in available)
#         close = sum(x["status"] == "CLOSE_MATCH" for x in available)
#         mismatches = sum(x["status"] == "MISMATCH" for x in available)

#         if mismatches >= 2:
#             status = "MISMATCH DETECTED"
#             reason = "Multiple important fields do not match the MRZ."
#         elif mismatches == 0 and confidence >= 90:
#             status = "VERIFIED"
#             reason = "The extracted visa fields are consistent with the MRZ."
#         elif confidence >= 75:
#             status = "REVIEW REQUIRED"
#             reason = "Some fields are close matches; manual review is recommended."
#         else:
#             status = "CLEARER IMAGE REQUIRED"
#             reason = "The extracted information is not reliable enough."

#         return {
#             "document_type": "VISA",
#             "status": status,
#             "confidence": confidence,
#             "matches": matches,
#             "close_matches": close,
#             "mismatches": mismatches,
#             "reason": reason,
#             "checks": checks,
#         }

#     def process(self, image_path):
#         image = self.load_image(image_path)
#         processed = self.preprocess(image)
#         ocr_data = self.ocr(processed)

#         quality = self.check_image_quality(ocr_data)

#         if not quality["clear"]:
#             return {
#                 "document_type": "VISA",
#                 "status": "CLEARER IMAGE REQUIRED",
#                 "ocr_confidence": round(quality["confidence"] * 100, 2),
#                 "reason": quality["reason"],
#             }

#         visa_data = self.extract_fields(ocr_data)
#         mrz_data = self.extract_mrz(image)

#         result = self.verify(visa_data, mrz_data)

#         result["ocr_confidence"] = round(
#             quality["confidence"] * 100, 2
#         )
#         result["fields"] = visa_data
#         result["mrz"] = mrz_data

#         return result

#     @staticmethod
#     def print_result(result):
#         print("\n" + "=" * 60)
#         print("                    VISA RESULT")
#         print("=" * 60)
#         print(f"STATUS      : {result.get('status', 'UNKNOWN')}")
#         if "confidence" in result:
#             print(f"CONFIDENCE  : {result['confidence']}%")
#         if "ocr_confidence" in result:
#             print(f"OCR CONF.   : {result['ocr_confidence']}%")
#         print(f"REASON      : {result.get('reason', '')}")
#         print("=" * 60)

#         if result.get("status") == "CLEARER IMAGE REQUIRED":
#             print("Please upload a clearer visa image.")
#         elif result.get("status") == "VERIFIED":
#             print("Visa data is internally consistent with the MRZ.")
#         elif result.get("status") == "REVIEW REQUIRED":
#             print("Manual review is recommended.")
#         elif result.get("status") == "MISMATCH DETECTED":
#             print("Important fields do not match the MRZ.")
#         print("=" * 60)


# if __name__ == "__main__":
#     visa = VisaOCR()
#     result = visa.process("images/visa.jpg")
#     visa.print_result(result)


"""
visa_ocr.py

Modular Visa OCR + flexible field extraction + MRZ consistency checking.

IMPORTANT:
This module performs OCR-based extraction and internal consistency checks.
A successful result does NOT prove that a visa was genuinely issued by a
government authority.

The module intentionally does not depend on one fixed visa template.
"""

import re
from pathlib import Path
from difflib import SequenceMatcher

import cv2
import easyocr


class VisaOCR:
    """
    Flexible OCR processor for visa documents.

    Designed to handle different visa layouts instead of relying on
    fixed coordinates.
    """

    def __init__(self, languages=None, gpu=False, reader=None):

        self.reader = reader or easyocr.Reader(
            languages or ["en"],
            gpu=gpu
        )

    # ============================================================
    # IMAGE
    # ============================================================

    @staticmethod
    def load_image(image_path):

        path = Path(image_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Visa image not found: {path}"
            )

        image = cv2.imread(str(path))

        if image is None:
            raise ValueError(
                f"Could not decode visa image: {path}"
            )

        return image

    # ============================================================
    # NORMALIZATION
    # ============================================================

    @staticmethod
    def normalize(value):

        if not value:
            return ""

        return re.sub(
            r"[^A-Z0-9]",
            "",
            str(value).upper()
        )

    @staticmethod
    def normalize_name(value):

        if not value:
            return ""

        value = str(value).upper()

        value = value.replace("<", " ")

        value = re.sub(
            r"[^A-Z ]",
            "",
            value
        )

        value = re.sub(
            r"\s+",
            " ",
            value
        )

        return value.strip()

    @staticmethod
    def clean_text(value):

        if not value:
            return ""

        return re.sub(
            r"\s+",
            " ",
            str(value)
        ).strip()

    # ============================================================
    # IMAGE PREPROCESSING
    # ============================================================

    @staticmethod
    def preprocess_variants(image):

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY
        )

        # Variant 1 - original grayscale
        variant_1 = gray

        # Variant 2 - contrast enhancement
        clahe = cv2.createCLAHE(
            clipLimit=2.0,
            tileGridSize=(8, 8)
        )

        variant_2 = clahe.apply(gray)

        # Variant 3 - OTSU
        _, variant_3 = cv2.threshold(
            gray,
            0,
            255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )

        # Variant 4 - adaptive threshold
        variant_4 = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            11
        )

        return [
            variant_1,
            variant_2,
            variant_3,
            variant_4
        ]

    # ============================================================
    # OCR
    # ============================================================

    def run_ocr(self, image):

        results = self.reader.readtext(
            image,
            paragraph=False,
            detail=1
        )

        data = []

        for bbox, text, confidence in results:

            text = self.clean_text(text)

            if not text:
                continue

            data.append({
                "text": text,
                "confidence": float(confidence),
                "bbox": bbox
            })

        return data

    def multi_pass_ocr(self, image):

        variants = self.preprocess_variants(image)

        all_results = []

        for variant in variants:

            results = self.run_ocr(variant)

            all_results.extend(results)

        return self.remove_duplicate_text(all_results)

    # ============================================================
    # REMOVE DUPLICATES
    # ============================================================

    @staticmethod
    def remove_duplicate_text(results):

        unique = []

        for item in results:

            text_normalized = re.sub(
                r"[^A-Z0-9]",
                "",
                item["text"].upper()
            )

            if not text_normalized:
                continue

            duplicate = False

            for existing in unique:

                existing_normalized = re.sub(
                    r"[^A-Z0-9]",
                    "",
                    existing["text"].upper()
                )

                similarity = SequenceMatcher(
                    None,
                    text_normalized,
                    existing_normalized
                ).ratio()

                if similarity >= 0.90:

                    if (
                        item["confidence"]
                        > existing["confidence"]
                    ):
                        existing.update(item)

                    duplicate = True
                    break

            if not duplicate:
                unique.append(item)

        return unique

    # ============================================================
    # IMAGE QUALITY
    # ============================================================

    @staticmethod
    def check_image_quality(
        ocr_data,
        minimum_confidence=0.50
    ):

        if not ocr_data:

            return {
                "clear": False,
                "confidence": 0.0,
                "reason": "No readable text was detected."
            }

        confidences = [
            x["confidence"]
            for x in ocr_data
        ]

        average = sum(confidences) / len(confidences)

        readable = sum(
            confidence >= 0.40
            for confidence in confidences
        )

        if readable < 2:

            return {
                "clear": False,
                "confidence": average,
                "reason": "Not enough readable visa text was detected."
            }

        if average < minimum_confidence:

            return {
                "clear": False,
                "confidence": average,
                "reason": "OCR confidence is too low."
            }

        return {
            "clear": True,
            "confidence": average,
            "reason": "Image quality is sufficient."
        }

    # ============================================================
    # FULL OCR TEXT
    # ============================================================

    @staticmethod
    def get_full_text(ocr_data):

        return " ".join(
            item["text"]
            for item in ocr_data
        )

    # ============================================================
    # DATE DETECTION
    # ============================================================

    @staticmethod
    def extract_dates(text):

        patterns = [

            # DD/MM/YYYY
            r"\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b",

            # YYYY/MM/DD
            r"\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b",

            # DD-MM-YY
            r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2}\b",

            # DD MON YYYY
            r"\b\d{1,2}\s+"
            r"(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)"
            r"\s+\d{4}\b"
        ]

        dates = []

        upper_text = text.upper()

        for pattern in patterns:

            matches = re.findall(
                pattern,
                upper_text
            )

            for match in matches:

                if match not in dates:
                    dates.append(match)

        return dates

    # ============================================================
    # PASSPORT NUMBER DETECTION
    # ============================================================

    @staticmethod
    def extract_passport_numbers(text):

        candidates = []

        tokens = re.findall(
            r"\b[A-Z0-9]{6,12}\b",
            text.upper()
        )

        for token in tokens:

            # Passport numbers generally contain
            # letters/numbers and are not long words.
            if not any(c.isdigit() for c in token):
                continue

            if len(token) < 6 or len(token) > 12:
                continue

            candidates.append(token)

        return list(dict.fromkeys(candidates))

    # ============================================================
    # VISA NUMBER DETECTION
    # ============================================================

    @staticmethod
    def extract_visa_numbers(text):

        patterns = [

            r"(?:VISA\s*(?:NO|NUMBER|#)?\s*[:\-]?\s*)"
            r"([A-Z0-9]{5,20})",

            r"(?:CONTROL\s*(?:NO|NUMBER|#)?\s*[:\-]?\s*)"
            r"([A-Z0-9]{5,20})",

            r"(?:REFERENCE\s*(?:NO|NUMBER|#)?\s*[:\-]?\s*)"
            r"([A-Z0-9]{5,20})",
        ]

        results = []

        upper_text = text.upper()

        for pattern in patterns:

            matches = re.findall(
                pattern,
                upper_text
            )

            results.extend(matches)

        return list(dict.fromkeys(results))

    # ============================================================
    # NATIONALITY
    # ============================================================

    @staticmethod
    def extract_nationality(text):

        patterns = [

            r"(?:NATIONALITY|NATIONALITY/COUNTRY)"
            r"\s*[:\-]?\s*([A-Z][A-Z ]{2,30})",

            r"(?:COUNTRY)"
            r"\s*[:\-]?\s*([A-Z][A-Z ]{2,30})",
        ]

        upper_text = text.upper()

        for pattern in patterns:

            match = re.search(
                pattern,
                upper_text
            )

            if match:
                return match.group(1).strip()

        return None

    # ============================================================
    # VISA TYPE
    # ============================================================

    @staticmethod
    def extract_visa_type(text):

        patterns = [

            r"(?:VISA\s*TYPE)"
            r"\s*[:\-]?\s*([A-Z0-9 /-]{2,30})",

            r"(?:TYPE\s*(?:OF)?\s*VISA)"
            r"\s*[:\-]?\s*([A-Z0-9 /-]{2,30})",

            r"(?:CLASS)"
            r"\s*[:\-]?\s*([A-Z0-9 /-]{1,20})",
        ]

        upper_text = text.upper()

        for pattern in patterns:

            match = re.search(
                pattern,
                upper_text
            )

            if match:
                return match.group(1).strip()

        return None

    # ============================================================
    # LABEL BASED EXTRACTION
    # ============================================================

    def find_after_label(
        self,
        ocr_data,
        labels
    ):

        for index, item in enumerate(ocr_data):

            text = item["text"].upper()

            for label in labels:

                if label.upper() in text:

                    # Check following OCR items.
                    for next_item in ocr_data[
                        index + 1:index + 4
                    ]:

                        candidate = next_item["text"].strip()

                        if candidate:

                            return candidate

        return None

    # ============================================================
    # FIELD EXTRACTION
    # ============================================================

    def extract_fields(self, ocr_data):

        full_text = self.get_full_text(
            ocr_data
        )

        dates = self.extract_dates(
            full_text
        )

        passport_numbers = (
            self.extract_passport_numbers(
                full_text
            )
        )

        visa_numbers = (
            self.extract_visa_numbers(
                full_text
            )
        )

        fields = {

            "name": self.find_after_label(
                ocr_data,
                [
                    "NAME",
                    "FULL NAME",
                    "SURNAME",
                    "GIVEN NAME",
                    "APPLICANT NAME"
                ]
            ),

            "surname": self.find_after_label(
                ocr_data,
                [
                    "SURNAME",
                    "LAST NAME",
                    "FAMILY NAME"
                ]
            ),

            "given_name": self.find_after_label(
                ocr_data,
                [
                    "GIVEN NAME",
                    "FIRST NAME",
                    "GIVEN NAMES"
                ]
            ),

            "passport_number": self.find_after_label(
                ocr_data,
                [
                    "PASSPORT NUMBER",
                    "PASSPORT NO",
                    "PASSPORT #"
                ]
            ),

            "visa_number": self.find_after_label(
                ocr_data,
                [
                    "VISA NUMBER",
                    "VISA NO",
                    "VISA #",
                    "CONTROL NUMBER",
                    "REFERENCE NUMBER"
                ]
            ),

            "nationality": self.extract_nationality(
                full_text
            ),

            "visa_type": self.extract_visa_type(
                full_text
            ),

            "dates": dates,

            "passport_candidates": passport_numbers,

            "visa_candidates": visa_numbers,

            "sex": self.find_after_label(
                ocr_data,
                [
                    "SEX",
                    "GENDER"
                ]
            ),

            "birth_date": self.find_after_label(
                ocr_data,
                [
                    "BIRTH DATE",
                    "DATE OF BIRTH",
                    "DOB"
                ]
            ),

            "issue_date": self.find_after_label(
                ocr_data,
                [
                    "ISSUE DATE",
                    "DATE OF ISSUE",
                    "ISSUED"
                ]
            ),

            "expiration_date": self.find_after_label(
                ocr_data,
                [
                    "EXPIRATION DATE",
                    "EXPIRY DATE",
                    "DATE OF EXPIRY",
                    "VALID UNTIL"
                ]
            ),

            "issuing_post": self.find_after_label(
                ocr_data,
                [
                    "ISSUING POST",
                    "ISSUING POST NAME",
                    "ISSUED AT",
                    "PLACE OF ISSUE"
                ]
            ),
        }

        return fields

    # ============================================================
    # MRZ CLEANING
    # ============================================================

    @staticmethod
    def clean_mrz(text):

        text = text.upper()

        replacements = {
            "«": "<",
            "‹": "<",
            "_": "<",
            "—": "<",
            " ": ""
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        return re.sub(
            r"[^A-Z0-9<]",
            "",
            text
        )

    # ============================================================
    # MRZ DETECTION
    # ============================================================

    def extract_mrz(self, image):

        h, w = image.shape[:2]

        # Search several lower portions rather than
        # assuming one exact MRZ position.
        regions = [

            image[int(h * 0.55):h, :],

            image[int(h * 0.65):h, :],

            image[int(h * 0.45):h, :]
        ]

        detected_lines = []

        for region in regions:

            results = self.reader.readtext(
                region,
                paragraph=False,
                detail=1
            )

            for bbox, text, confidence in results:

                cleaned = self.clean_mrz(text)

                if len(cleaned) >= 20:

                    detected_lines.append({
                        "text": cleaned,
                        "confidence": float(confidence),
                        "bbox": bbox
                    })

        if not detected_lines:

            return {
                "valid": False,
                "reason": "MRZ was not detected."
            }

        # Remove duplicate lines.
        unique_lines = []

        for item in detected_lines:

            duplicate = False

            for existing in unique_lines:

                similarity = SequenceMatcher(
                    None,
                    item["text"],
                    existing["text"]
                ).ratio()

                if similarity >= 0.85:

                    if (
                        item["confidence"]
                        > existing["confidence"]
                    ):
                        existing.update(item)

                    duplicate = True
                    break

            if not duplicate:
                unique_lines.append(item)

        # Sort by vertical position.
        unique_lines.sort(
            key=lambda x: x["bbox"][0][0]
        )

        if len(unique_lines) < 2:

            return {
                "valid": False,
                "reason": "Two MRZ lines were not detected."
            }

        line1 = unique_lines[0]["text"]

        line2 = unique_lines[1]["text"]

        line1 = line1.ljust(44, "<")[:44]

        line2 = line2.ljust(44, "<")[:44]

        # Passport TD3 MRZ structure.
        if (
            line1[0] not in ["P", "V"]
            and line2[0].isalnum()
        ):

            return {
                "valid": False,
                "reason": "Detected text does not appear to be a standard MRZ."
            }

        name_parts = line1[5:44].split(
            "<<",
            1
        )

        surname = (
            name_parts[0]
            .replace("<", " ")
            .strip()
        )

        given_name = ""

        if len(name_parts) > 1:

            given_name = (
                name_parts[1]
                .replace("<", " ")
                .strip()
            )

        return {

            "valid": True,

            "document_code": line1[:2],

            "issuing_country": line1[2:5],

            "surname": surname,

            "given_name": given_name,

            "passport_number": (
                line2[:9]
                .replace("<", "")
            ),

            "nationality": (
                line2[10:13]
                .replace("<", "")
            ),

            "birth_date": line2[13:19],

            "sex": line2[20],

            "expiration_date": line2[21:27],

            "personal_number": (
                line2[28:42]
                .replace("<", "")
            ),

            "raw_line1": line1,

            "raw_line2": line2,

            "mrz_confidence": round(
                (
                    unique_lines[0]["confidence"]
                    +
                    unique_lines[1]["confidence"]
                ) / 2,
                3
            )
        }

    # ============================================================
    # FIELD COMPARISON
    # ============================================================

    def compare(
        self,
        visual,
        mrz,
        field
    ):

        if not visual or not mrz:

            return {
                "status": "NOT_AVAILABLE",
                "similarity": 0.0
            }

        if field in [
            "surname",
            "given_name"
        ]:

            a = self.normalize_name(
                visual
            )

            b = self.normalize_name(
                mrz
            )

        else:

            a = self.normalize(
                visual
            )

            b = self.normalize(
                mrz
            )

        if not a or not b:

            return {
                "status": "NOT_AVAILABLE",
                "similarity": 0.0
            }

        similarity = SequenceMatcher(
            None,
            a,
            b
        ).ratio()

        if a == b:

            status = "MATCH"

        elif similarity >= 0.85:

            status = "CLOSE_MATCH"

        else:

            status = "MISMATCH"

        return {

            "visual_value": visual,

            "mrz_value": mrz,

            "status": status,

            "similarity": round(
                similarity,
                3
            )
        }

    # ============================================================
    # VERIFICATION
    # ============================================================

    def verify(
        self,
        fields,
        mrz
    ):

        if not mrz.get("valid"):

            return {

                "document_type": "VISA",

                "status": "VISA DATA DETECTED",

                "reason":
                    "Visa text was detected, but a reliable MRZ "
                    "was not available for cross-validation."
            }

        checks = {}

        comparison_fields = [
            "passport_number",
            "surname",
            "given_name",
            "nationality",
            "birth_date",
            "sex",
            "expiration_date"
        ]

        for field in comparison_fields:

            checks[field] = self.compare(
                fields.get(field),
                mrz.get(field),
                field
            )

        available = [

            value
            for value in checks.values()

            if value["status"]
            != "NOT_AVAILABLE"
        ]

        if not available:

            return {

                "document_type": "VISA",

                "status":
                    "CLEARER IMAGE REQUIRED",

                "reason":
                    "No reliable fields could be "
                    "cross-validated.",

                "checks": checks
            }

        matches = sum(
            x["status"] == "MATCH"
            for x in available
        )

        close_matches = sum(
            x["status"] == "CLOSE_MATCH"
            for x in available
        )

        mismatches = sum(
            x["status"] == "MISMATCH"
            for x in available
        )

        confidence = (
            sum(
                x["similarity"]
                for x in available
            )
            /
            len(available)
        ) * 100

        confidence = round(
            confidence,
            2
        )

        # Strong consistency
        if (
            mismatches == 0
            and matches >= 2
            and confidence >= 85
        ):

            status = "VERIFIED"

            reason = (
                "Visa fields are internally consistent "
                "with the detected MRZ."
            )

        # Multiple contradictions
        elif mismatches >= 2:

            status = "MISMATCH DETECTED"

            reason = (
                "Multiple extracted fields do not "
                "match the MRZ."
            )

        # Weak OCR
        elif confidence < 70:

            status = "CLEARER IMAGE REQUIRED"

            reason = (
                "The extracted information is not "
                "reliable enough."
            )

        else:

            status = "REVIEW REQUIRED"

            reason = (
                "Some fields require manual review."
            )

        return {

            "document_type": "VISA",

            "status": status,

            "confidence": confidence,

            "matches": matches,

            "close_matches": close_matches,

            "mismatches": mismatches,

            "reason": reason,

            "checks": checks
        }

    # ============================================================
    # MAIN PROCESS
    # ============================================================

    def process(
        self,
        image_path
    ):

        image = self.load_image(
            image_path
        )

        print("Running multi-pass OCR...")

        ocr_data = self.multi_pass_ocr(
            image
        )

        quality = self.check_image_quality(
            ocr_data
        )

        if not quality["clear"]:

            return {

                "document_type": "VISA",

                "status":
                    "CLEARER IMAGE REQUIRED",

                "ocr_confidence":
                    round(
                        quality["confidence"] * 100,
                        2
                    ),

                "reason":
                    quality["reason"]
            }

        fields = self.extract_fields(
            ocr_data
        )

        mrz = self.extract_mrz(
            image
        )

        result = self.verify(
            fields,
            mrz
        )

        result["ocr_confidence"] = round(
            quality["confidence"] * 100,
            2
        )

        result["fields"] = fields

        result["mrz"] = mrz

        result["ocr_matches"] = len(
            ocr_data
        )

        return result

    # ============================================================
    # RESULT DISPLAY
    # ============================================================

    @staticmethod
    def print_result(result):

        print("\n" + "=" * 60)

        print(
            "                 VISA OCR RESULT"
        )

        print("=" * 60)

        print(
            f"STATUS      : "
            f"{result.get('status', 'UNKNOWN')}"
        )

        if "confidence" in result:

            print(
                f"CONFIDENCE  : "
                f"{result['confidence']}%"
            )

        if "ocr_confidence" in result:

            print(
                f"OCR CONF.   : "
                f"{result['ocr_confidence']}%"
            )

        if "ocr_matches" in result:

            print(
                f"OCR MATCHES : "
                f"{result['ocr_matches']}"
            )

        print(
            f"REASON      : "
            f"{result.get('reason', '')}"
        )

        print("=" * 60)

        if result.get("status") == "CLEARER IMAGE REQUIRED":

            print(
                "Please upload a clearer visa image."
            )

        elif result.get("status") == "VERIFIED":

            print(
                "Visa OCR data is internally "
                "consistent with the MRZ."
            )

        elif result.get("status") == "MISMATCH DETECTED":

            print(
                "Important visa fields do not "
                "match the MRZ."
            )

        elif result.get("status") == "REVIEW REQUIRED":

            print(
                "Manual verification is recommended."
            )

        elif result.get("status") == "VISA DATA DETECTED":

            print(
                "Visa information was detected, "
                "but MRZ verification was unavailable."
            )

        print("=" * 60)


# ================================================================
# DIRECT TEST
# ================================================================

if __name__ == "__main__":

    visa = VisaOCR()

    result = visa.process(
        "visa.jpg"
    )

    visa.print_result(result)