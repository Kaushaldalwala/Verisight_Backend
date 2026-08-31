"""
driving_license_ocr.py

Indian Driving Licence OCR for the supplied DL card layout.

Extracts:
    - Licence / ANO number
    - Date of Issue
    - Validity
    - Date of Birth
    - Blood Group
    - Name
    - Son/Daughter/Wife of

The extractor uses region-based OCR instead of generic label/value
matching because the supplied licence has a consistent visual layout.

IMPORTANT:
OCR extraction is not proof of authenticity or government issuance.
"""

import re
from pathlib import Path

import cv2
import easyocr


class DrivingLicenseOCR:

    document_type = "DRIVING LICENSE"

    def __init__(self, languages=None, gpu=False):

        print("Initializing Driving License OCR...")

        self.reader = easyocr.Reader(
            languages or ["en"],
            gpu=gpu
        )

    # ============================================================
    # IMAGE
    # ============================================================

    def load_image(self, image_path):

        path = Path(image_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Driving licence image not found: {path}"
            )

        image = cv2.imread(str(path))

        if image is None:
            raise ValueError(
                f"Could not decode image: {path}"
            )

        return image

    # ============================================================
    # UPSCALE
    # ============================================================

    def prepare_image(self, image):

        h, w = image.shape[:2]

        # Your sample is ~500px wide.
        # Make it much larger before OCR.

        target_width = 2000

        if w < target_width:

            scale = target_width / w

            image = cv2.resize(
                image,
                None,
                fx=scale,
                fy=scale,
                interpolation=cv2.INTER_CUBIC
            )

        return image

    # ============================================================
    # OCR ONE REGION
    # ============================================================

    def ocr_region(self, image, name):

        results = self.reader.readtext(
            image,
            paragraph=False,
            detail=1,
            text_threshold=0.4,
            low_text=0.2,
            link_threshold=0.2,
            width_ths=0.8,
            mag_ratio=1.5
        )

        output = []

        for bbox, text, confidence in results:

            text = str(text).strip()

            if not text:
                continue

            output.append({
                "text": text,
                "confidence": float(confidence),
                "bbox": bbox
            })

        return output

    # ============================================================
    # OCR TEXT ONLY
    # ============================================================

    def read_region(self, image, name):

        results = self.ocr_region(
            image,
            name
        )

        if not results:
            return ""

        # Sort by confidence.
        results.sort(
            key=lambda x: x["confidence"],
            reverse=True
        )

        # Combine all detected text.
        text = " ".join(
            item["text"]
            for item in results
        )

        return text.strip()

    # ============================================================
    # DATE NORMALIZATION
    # ============================================================

    @staticmethod
    def normalize_date(text):

        if not text:
            return None

        text = text.upper()

        # Common OCR mistakes.
        replacements = {
            "O": "0",
            "Q": "0",
            "I": "1",
            "L": "1",
            "|": "1",
            "\\": "/",
            "-": "/",
            ".": "/",
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        # Remove spaces around separators.
        text = re.sub(
            r"\s*/\s*",
            "/",
            text
        )

        # Find DD/MM/YYYY
        matches = re.findall(
            r"(?<!\d)(\d{1,2}/\d{1,2}/\d{4})(?!\d)",
            text
        )

        if not matches:
            return None

        for value in matches:

            parts = value.split("/")

            if len(parts) != 3:
                continue

            day = int(parts[0])
            month = int(parts[1])
            year = int(parts[2])

            if (
                1 <= day <= 31
                and 1 <= month <= 12
                and 1900 <= year <= 2100
            ):
                return (
                    f"{day:02d}/"
                    f"{month:02d}/"
                    f"{year:04d}"
                )

        return None

    # ============================================================
    # FIND ALL DATES
    # ============================================================

    @staticmethod
    def find_dates(text):

        if not text:
            return []

        text = text.upper()

        replacements = {
            "O": "0",
            "Q": "0",
            "I": "1",
            "L": "1",
            "|": "1",
            "-": "/",
            ".": "/",
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        text = re.sub(
            r"\s*/\s*",
            "/",
            text
        )

        raw = re.findall(
            r"\d{1,2}/\d{1,2}/\d{4}",
            text
        )

        dates = []

        for value in raw:

            normalized = DrivingLicenseOCR.normalize_date(
                value
            )

            if normalized and normalized not in dates:
                dates.append(normalized)

        return dates

    # ============================================================
    # LICENSE NUMBER
    # ============================================================

    @staticmethod
    def normalize_license_number(text):

        if not text:
            return None

        text = text.upper()

        # Common OCR substitutions.
        text = text.replace("O", "0")
        text = text.replace("I", "1")
        text = text.replace("L", "1")

        # Keep digits only.
        digits = re.sub(
            r"\D",
            "",
            text
        )

        # This particular sample:
        # 20130003278
        #
        # Accept 8-20 digits so other Indian DL
        # numbers can also be handled.

        if 8 <= len(digits) <= 20:
            return digits

        return None

    # ============================================================
    # BLOOD GROUP
    # ============================================================

    @staticmethod
    def extract_blood_group(text):

        if not text:
            return None

        text = text.upper()

        # Normalize common OCR spacing.
        text = re.sub(
            r"\s+",
            "",
            text
        )

        patterns = [
            r"\bAB[+-]\b",
            r"\bA[+-]\b",
            r"\bB[+-]\b",
            r"\bO[+-]\b"
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                text
            )

            if match:
                return match.group()

        return None

    # ============================================================
    # NAME CLEANING
    # ============================================================

    @staticmethod
    def clean_name(text):

        if not text:
            return None

        text = text.upper()

        # Remove common OCR noise.
        text = re.sub(
            r"[^A-Z .]",
            " ",
            text
        )

        text = re.sub(
            r"\s+",
            " ",
            text
        ).strip()

        # Remove obvious labels.
        bad_words = [
            "NAME",
            "DRIVING",
            "LICENCE",
            "LICENSE",
            "UNION",
            "INDIA",
            "DATE",
            "BIRTH",
            "BLOOD",
            "GROUP",
            "VALIDITY",
            "ISSUE"
        ]

        words = text.split()

        words = [
            word
            for word in words
            if word not in bad_words
        ]

        if not words:
            return None

        return " ".join(words)

    # ============================================================
    # RELATION CLEANING
    # ============================================================

    @staticmethod
    def clean_relation(text):

        if not text:
            return None

        text = text.upper()

        # Remove the label if OCR captured it.

        patterns = [
            r".*SON/DAUGHTER/WIFE\s+OF",
            r".*SON/DAUGHTER/ WIFE\s+OF",
            r".*SON\s*/?\s*DAUGHTER\s*/?\s*WIFE\s+OF",
            r".*SON\s+DAUGHTER\s+WIFE\s+OF",
            r".*DAUGHTER/WIFE\s+OF",
            r".*WIFE\s+OF",
        ]

        for pattern in patterns:

            cleaned = re.sub(
                pattern,
                "",
                text,
                flags=re.IGNORECASE
            )

            if cleaned != text:
                text = cleaned
                break

        text = re.sub(
            r"[^A-Z .]",
            " ",
            text
        )

        text = re.sub(
            r"\s+",
            " ",
            text
        ).strip()

        if len(text) < 2:
            return None

        return text

    # ============================================================
    # FIELD ROI
    # ============================================================

    def crop_regions(self, image):

        h, w = image.shape[:2]

        """
        Coordinates are proportional to the supplied template.

        Original sample:
            ~500 x 333

        We use percentages rather than fixed pixels so the same
        layout works at different resolutions.
        """

        regions = {

            # Top:
            # ANO1 20130003278
            "license_number": (
                0.12,
                0.08,
                0.72,
                0.25
            ),

            # Date of Issue
            "date_of_issue": (
                0.27,
                0.25,
                0.54,
                0.43
            ),

            # Validity
            "validity": (
                0.52,
                0.25,
                0.82,
                0.43
            ),

            # Date of Birth
            "date_of_birth": (
                0.27,
                0.38,
                0.54,
                0.55
            ),

            # Blood group
            "blood_group": (
                0.52,
                0.38,
                0.78,
                0.55
            ),

            # Name
            "name": (
                0.02,
                0.53,
                0.58,
                0.73
            ),

            # Relation
            "relation": (
                0.02,
                0.66,
                0.70,
                0.88
            ),
        }

        output = {}

        for key, (
            x1,
            y1,
            x2,
            y2
        ) in regions.items():

            left = int(w * x1)
            top = int(h * y1)
            right = int(w * x2)
            bottom = int(h * y2)

            crop = image[
                top:bottom,
                left:right
            ]

            output[key] = crop

        return output

    # ============================================================
    # EXTRACT
    # ============================================================

    def extract_fields(self, image):

        regions = self.crop_regions(
            image
        )

        fields = {}

        # --------------------------------------------------------
        # LICENSE NUMBER
        # --------------------------------------------------------

        text = self.read_region(
            regions["license_number"],
            "license_number"
        )

        print(
            f"[LICENSE NUMBER OCR] {text}"
        )

        number = self.normalize_license_number(
            text
        )

        if number:

            fields["license_number"] = {
                "value": number,
                "confidence": 0.0,
                "raw": text
            }

        # --------------------------------------------------------
        # ISSUE DATE
        # --------------------------------------------------------

        text = self.read_region(
            regions["date_of_issue"],
            "date_of_issue"
        )

        print(
            f"[ISSUE DATE OCR] {text}"
        )

        dates = self.find_dates(text)

        if dates:

            fields["date_of_issue"] = {
                "value": dates[0],
                "confidence": 0.0,
                "raw": text
            }

        # --------------------------------------------------------
        # VALIDITY
        # --------------------------------------------------------

        text = self.read_region(
            regions["validity"],
            "validity"
        )

        print(
            f"[VALIDITY OCR] {text}"
        )

        dates = self.find_dates(text)

        if dates:

            fields["validity"] = {
                "value": dates[0],
                "confidence": 0.0,
                "raw": text
            }

        # --------------------------------------------------------
        # DATE OF BIRTH
        # --------------------------------------------------------

        text = self.read_region(
            regions["date_of_birth"],
            "date_of_birth"
        )

        print(
            f"[DOB OCR] {text}"
        )

        dates = self.find_dates(text)

        if dates:

            fields["date_of_birth"] = {
                "value": dates[0],
                "confidence": 0.0,
                "raw": text
            }

        # --------------------------------------------------------
        # BLOOD GROUP
        # --------------------------------------------------------

        text = self.read_region(
            regions["blood_group"],
            "blood_group"
        )

        print(
            f"[BLOOD GROUP OCR] {text}"
        )

        blood = self.extract_blood_group(
            text
        )

        if blood:

            fields["blood_group"] = {
                "value": blood,
                "confidence": 0.0,
                "raw": text
            }

        # --------------------------------------------------------
        # NAME
        # --------------------------------------------------------

        text = self.read_region(
            regions["name"],
            "name"
        )

        print(
            f"[NAME OCR] {text}"
        )

        name = self.clean_name(
            text
        )

        if name:

            fields["name"] = {
                "value": name,
                "confidence": 0.0,
                "raw": text
            }

        # --------------------------------------------------------
        # RELATION
        # --------------------------------------------------------

        text = self.read_region(
            regions["relation"],
            "relation"
        )

        print(
            f"[RELATION OCR] {text}"
        )

        relation = self.clean_relation(
            text
        )

        if relation:

            fields["relation"] = {
                "value": relation,
                "confidence": 0.0,
                "raw": text
            }

        return fields

    # ============================================================
    # PROCESS
    # ============================================================

    def process(self, image_path):

        image = self.load_image(
            image_path
        )

        image = self.prepare_image(
            image
        )

        print(
            f"Image size after upscale: "
            f"{image.shape[1]} x {image.shape[0]}"
        )

        print("\nRunning OCR...\n")

        fields = self.extract_fields(
            image
        )

        important = [
            "license_number",
            "date_of_issue",
            "validity",
            "date_of_birth",
            "blood_group",
            "name",
            "relation"
        ]

        detected = sum(
            field in fields
            for field in important
        )

        if detected >= 5:

            status = "OCR SUCCESS"

            reason = (
                "Driving licence information was "
                "successfully extracted."
            )

        elif detected >= 3:

            status = "REVIEW REQUIRED"

            reason = (
                "Several fields were detected, "
                "but manual review is recommended."
            )

        else:

            status = "CLEARER IMAGE REQUIRED"

            reason = (
                "Insufficient driving licence information "
                "could be extracted."
            )

        return {
            "document_type": self.document_type,
            "status": status,
            "ocr_confidence": 0.0,
            "reason": reason,
            "fields": fields
        }

    # ============================================================
    # PRINT
    # ============================================================

    @staticmethod
    def print_result(result):

        print("\n")
        print("=" * 65)
        print("             DRIVING LICENSE OCR RESULT")
        print("=" * 65)

        print(
            f"STATUS       : "
            f"{result.get('status', 'UNKNOWN')}"
        )

        print(
            f"OCR CONF.    : "
            f"{result.get('ocr_confidence', 0)}%"
        )

        print(
            f"REASON       : "
            f"{result.get('reason', '')}"
        )

        print("\nEXTRACTED FIELDS")
        print("-" * 65)

        fields = result.get(
            "fields",
            {}
        )

        names = {
            "license_number":
                "License Number",

            "date_of_issue":
                "Date of Issue",

            "validity":
                "Validity",

            "date_of_birth":
                "Date of Birth",

            "blood_group":
                "Blood Group",

            "name":
                "Name",

            "relation":
                "Son/Daughter/Wife of"
        }

        if not fields:

            print(
                "NO FIELDS DETECTED"
            )

        else:

            for key in [
                "license_number",
                "date_of_issue",
                "validity",
                "date_of_birth",
                "blood_group",
                "name",
                "relation"
            ]:

                if key not in fields:
                    continue

                value = fields[key]["value"]

                print(
                    f"{names[key]:<25} : {value}"
                )

        print("=" * 65)


if __name__ == "__main__":

    IMAGE_PATH = (
        r"D:\hackathons\SIH-2026\OCR"
        r"\ocr_modules\driving_license"
        r"\driving_license.jpg"
    )

    ocr = DrivingLicenseOCR(
        languages=["en"],
        gpu=False
    )

    result = ocr.process(
        IMAGE_PATH
    )

    ocr.print_result(
        result
    )