
# """
# aadhaar_ocr.py
# Modular Aadhaar OCR + format + Verhoeff checksum validation.

# IMPORTANT:
# Checksum validation only validates the extracted number's mathematical
# format. It does NOT prove that an Aadhaar document is genuine or issued
# by UIDAI.
# """

# import re
# from pathlib import Path

# import cv2
# import easyocr


# D_TABLE = [
#     [0,1,2,3,4,5,6,7,8,9],
#     [1,2,3,4,0,6,7,8,9,5],
#     [2,3,4,0,1,7,8,9,5,6],
#     [3,4,0,1,2,8,9,5,6,7],
#     [4,0,1,2,3,9,5,6,7,8],
#     [5,9,8,7,6,0,4,3,2,1],
#     [6,5,9,8,7,1,0,4,3,2],
#     [7,4,5,9,8,2,1,0,4,3],
#     [8,7,6,5,9,3,2,1,0,4],
#     [9,8,7,6,5,4,3,2,1,0],
# ]

# P_TABLE = [
#     [0,1,2,3,4,5,6,7,8,9],
#     [1,5,7,6,2,8,3,0,9,4],
#     [5,8,0,3,7,9,6,1,4,2],
#     [8,9,1,6,0,4,3,5,2,7],
#     [9,4,5,3,1,2,6,8,7,0],
#     [4,2,8,6,5,7,3,9,0,1],
#     [2,7,9,3,8,0,6,4,1,5],
#     [7,0,4,6,9,1,3,2,5,8],
# ]


# class AadhaarOCR:
#     def __init__(self, languages=None, gpu=False):
#         self.reader = easyocr.Reader(languages or ["en"], gpu=gpu)

#     def load_image(self, image_path):
#         path = Path(image_path)
#         if not path.exists():
#             raise FileNotFoundError(f"Aadhaar image not found: {path}")

#         image = cv2.imread(str(path))
#         if image is None:
#             raise ValueError(f"Could not decode image: {path}")
#         return image

#     def ocr(self, image):
#         gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

#         results = self.reader.readtext(
#             gray, paragraph=False, detail=1
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

#     def find_aadhaar_number(self, ocr_data):
#         # First look for a complete 12-digit OCR token.
#         for item in ocr_data:
#             cleaned = re.sub(r"[\s-]", "", item["text"])
#             match = re.search(r"\b\d{12}\b", cleaned)
#             if match:
#                 return match.group()

#         # Fallback: combine all OCR text.
#         full_text = " ".join(item["text"] for item in ocr_data)
#         digits = re.sub(r"\D", "", full_text)

#         matches = re.findall(r"\d{12}", digits)
#         return matches[0] if matches else None

#     @staticmethod
#     def verhoeff_validate(number):
#         if not number.isdigit() or len(number) != 12:
#             return False

#         checksum = 0

#         for i, digit in enumerate(map(int, number[::-1])):
#             checksum = D_TABLE[checksum][P_TABLE[i % 8][digit]]

#         return checksum == 0

#     def check_image_quality(self, ocr_data, aadhaar_number,
#                             minimum_average_confidence=0.50):
#         if not ocr_data:
#             return {
#                 "clear": False,
#                 "confidence": 0.0,
#                 "reason": "No readable text was detected."
#             }

#         avg = sum(x["confidence"] for x in ocr_data) / len(ocr_data)

#         if not aadhaar_number:
#             return {
#                 "clear": False,
#                 "confidence": avg,
#                 "reason": "The Aadhaar number could not be clearly detected."
#             }

#         if avg < minimum_average_confidence:
#             return {
#                 "clear": False,
#                 "confidence": avg,
#                 "reason": "OCR confidence is too low."
#             }

#         return {
#             "clear": True,
#             "confidence": avg,
#             "reason": "Image quality is sufficient."
#         }

#     def verify(self, aadhaar_number, ocr_data):
#         confidences = [x["confidence"] for x in ocr_data]
#         avg = sum(confidences) / len(confidences) if confidences else 0

#         format_valid = bool(
#             aadhaar_number
#             and aadhaar_number.isdigit()
#             and len(aadhaar_number) == 12
#         )

#         checksum_valid = (
#             self.verhoeff_validate(aadhaar_number)
#             if format_valid else False
#         )

#         if not format_valid:
#             status = "INVALID FORMAT"
#             reason = "A valid 12-digit Aadhaar number could not be extracted."
#         elif not checksum_valid:
#             status = "CHECKSUM FAILED"
#             reason = "The extracted number failed Verhoeff checksum validation."
#         elif avg < 0.60:
#             status = "REVIEW REQUIRED"
#             reason = "The number passed checksum validation, but OCR confidence is low."
#         else:
#             status = "VALIDATION PASSED"
#             reason = (
#                 "The extracted 12-digit number passed format and "
#                 "Verhoeff checksum validation."
#             )

#         masked = (
#             "XXXX XXXX " + aadhaar_number[-4:]
#             if aadhaar_number else "NOT DETECTED"
#         )

#         return {
#             "document_type": "AADHAAR",
#             "status": status,
#             "masked_number": masked,
#             "ocr_confidence": round(avg * 100, 2),
#             "format_valid": format_valid,
#             "checksum_valid": checksum_valid,
#             "reason": reason,
#         }

#     def process(self, image_path):
#         image = self.load_image(image_path)
#         ocr_data = self.ocr(image)
#         aadhaar_number = self.find_aadhaar_number(ocr_data)

#         quality = self.check_image_quality(
#             ocr_data, aadhaar_number
#         )

#         if not quality["clear"]:
#             return {
#                 "document_type": "AADHAAR",
#                 "status": "CLEARER IMAGE REQUIRED",
#                 "ocr_confidence": round(quality["confidence"] * 100, 2),
#                 "reason": quality["reason"],
#             }

#         result = self.verify(
#             aadhaar_number,
#             ocr_data
#         )

#         return result

#     @staticmethod
#     def print_result(result):
#         print("\n" + "=" * 60)
#         print("                 AADHAAR RESULT")
#         print("=" * 60)
#         print(f"STATUS      : {result.get('status', 'UNKNOWN')}")
#         print(f"AADHAAR NO. : {result.get('masked_number', 'NOT DETECTED')}")
#         print(f"OCR CONF.   : {result.get('ocr_confidence', 0)}%")
#         print(
#             f"FORMAT      : "
#             f"{'PASS' if result.get('format_valid') else 'FAIL'}"
#         )
#         print(
#             f"CHECKSUM    : "
#             f"{'PASS' if result.get('checksum_valid') else 'FAIL'}"
#         )
#         print(f"REASON      : {result.get('reason', '')}")
#         print("=" * 60)

#         if result.get("status") == "CLEARER IMAGE REQUIRED":
#             print("Please upload a clearer Aadhaar image.")
#         elif result.get("status") == "VALIDATION PASSED":
#             print("Number validation passed.")
#         elif result.get("status") == "REVIEW REQUIRED":
#             print("Manual review is recommended.")
#         print("=" * 60)


# if __name__ == "__main__":
#     aadhaar = AadhaarOCR()
#     result = aadhaar.process("images/aadhaar.jpg")
#     aadhaar.print_result(result)


# running script 
"""
aadhaar_ocr.py

Robust Aadhaar OCR module.

Designed for:
- Different Aadhaar layouts
- Horizontal and vertical cards
- High and low resolution images
- Numbers with spaces
- Numbers without spaces
- Multiple OCR preprocessing variants
- EasyOCR + optional Tesseract fallback

IMPORTANT:
OCR extraction is NOT proof of document authenticity.
Verhoeff validation is only a mathematical checksum check.
"""

import re
from pathlib import Path

import cv2
import easyocr

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


# ============================================================
# VERHOEFF TABLES
# ============================================================

D_TABLE = [
    [0,1,2,3,4,5,6,7,8,9],
    [1,2,3,4,0,6,7,8,9,5],
    [2,3,4,0,1,7,8,9,5,6],
    [3,4,0,1,2,8,9,5,6,7],
    [4,0,1,2,3,9,5,6,7,8],
    [5,9,8,7,6,0,4,3,2,1],
    [6,5,9,8,7,1,0,4,3,2],
    [7,4,5,9,8,2,1,0,4,3],
    [8,7,6,5,9,3,2,1,0,4],
    [9,8,7,6,5,4,3,2,1,0],
]

P_TABLE = [
    [0,1,2,3,4,5,6,7,8,9],
    [1,5,7,6,2,8,3,0,9,4],
    [5,8,0,3,7,9,6,1,4,2],
    [8,9,1,6,0,4,3,5,2,7],
    [9,4,5,3,1,2,6,8,7,0],
    [4,2,8,6,5,7,3,9,0,1],
    [2,7,9,3,8,0,6,4,1,5],
    [7,0,4,6,9,1,3,2,5,8],
]


class AadhaarOCR:

    def __init__(self, languages=None, gpu=False):

        self.reader = easyocr.Reader(
            languages or ["en"],
            gpu=gpu
        )

    # ========================================================
    # IMAGE LOADING
    # ========================================================

    def load_image(self, image_path):

        path = Path(image_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Aadhaar image not found: {path}"
            )

        image = cv2.imread(str(path))

        if image is None:
            raise ValueError(
                f"Could not decode image: {path}"
            )

        return image

    # ========================================================
    # IMAGE NORMALIZATION
    # ========================================================

    def resize_for_ocr(self, image):

        h, w = image.shape[:2]

        # Small images need significant enlargement.
        # Large images should not be enlarged unnecessarily.

        target_width = 1800

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

    # ========================================================
    # PREPROCESSING
    # ========================================================

    def create_variants(self, image):

        image = self.resize_for_ocr(image)

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY
        )

        # Contrast enhancement
        clahe = cv2.createCLAHE(
            clipLimit=2.0,
            tileGridSize=(8, 8)
        )

        enhanced = clahe.apply(gray)

        # Denoising
        denoised = cv2.fastNlMeansDenoising(
            enhanced,
            None,
            10,
            7,
            21
        )

        # Sharpen
        blur = cv2.GaussianBlur(
            denoised,
            (0, 0),
            3
        )

        sharpened = cv2.addWeighted(
            denoised,
            1.7,
            blur,
            -0.7,
            0
        )

        # OTSU
        _, otsu = cv2.threshold(
            sharpened,
            0,
            255,
            cv2.THRESH_BINARY +
            cv2.THRESH_OTSU
        )

        # Adaptive
        adaptive = cv2.adaptiveThreshold(
            sharpened,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            11
        )

        # Inverted versions can help with poor scans
        inverted = cv2.bitwise_not(
            otsu
        )

        return [
            image,
            gray,
            enhanced,
            sharpened,
            otsu,
            adaptive,
            inverted
        ]

    # ========================================================
    # EASY OCR
    # ========================================================

    def easyocr(self, image):

        try:

            results = self.reader.readtext(
                image,
                paragraph=False,
                detail=1,
                width_ths=0.7,
                text_threshold=0.5,
                low_text=0.3,
                link_threshold=0.3
            )

            output = []

            for bbox, text, confidence in results:

                text = text.strip()

                if not text:
                    continue

                output.append({
                    "text": text,
                    "confidence": float(confidence),
                    "bbox": bbox
                })

            return output

        except Exception as e:

            print(
                f"EasyOCR warning: {e}"
            )

            return []

    # ========================================================
    # TESSERACT
    # ========================================================

    def tesseract(self, image):

        if not TESSERACT_AVAILABLE:
            return []

        try:

            data = pytesseract.image_to_data(
                image,
                config="--psm 11",
                output_type=pytesseract.Output.DICT
            )

            results = []

            for i in range(
                len(data["text"])
            ):

                text = data["text"][i].strip()

                if not text:
                    continue

                try:
                    confidence = (
                        float(data["conf"][i]) / 100
                    )
                except:
                    continue

                if confidence <= 0:
                    continue

                x = data["left"][i]
                y = data["top"][i]
                w = data["width"][i]
                h = data["height"][i]

                bbox = [
                    [x, y],
                    [x + w, y],
                    [x + w, y + h],
                    [x, y + h]
                ]

                results.append({
                    "text": text,
                    "confidence": confidence,
                    "bbox": bbox
                })

            return results

        except Exception as e:

            print(
                f"Tesseract warning: {e}"
            )

            return []

    # ========================================================
    # NORMALIZE OCR TEXT
    # ========================================================

    @staticmethod
    def normalize_text(text):

        if not text:
            return ""

        return (
            str(text)
            .upper()
            .replace(" ", "")
            .replace("-", "")
            .replace("_", "")
        )

    # ========================================================
    # EXTRACT NUMBER CANDIDATES
    # ========================================================

    def extract_candidates(self, text):

        if not text:
            return []

        text = str(text)

        candidates = []

        # ----------------------------------------------------
        # Exact grouped form
        #
        # 1234 5678 9012
        # ----------------------------------------------------

        grouped = re.findall(
            r"(?<!\d)"
            r"\d{4}\s+\d{4}\s+\d{4}"
            r"(?!\d)",
            text
        )

        for value in grouped:

            number = re.sub(
                r"\D",
                "",
                value
            )

            if len(number) == 12:

                candidates.append(
                    number
                )

        # ----------------------------------------------------
        # Unspaced form
        #
        # 123456789012
        # ----------------------------------------------------

        direct = re.findall(
            r"(?<!\d)\d{12}(?!\d)",
            text
        )

        candidates.extend(
            direct
        )

        # ----------------------------------------------------
        # OCR sometimes returns:
        #
        # 1234
        # 5678
        # 9012
        #
        # This method is handled separately.
        # ----------------------------------------------------

        return list(
            dict.fromkeys(candidates)
        )

    # ========================================================
    # COMBINE OCR TOKENS
    # ========================================================

    def combine_numeric_tokens(
        self,
        ocr_data
    ):

        numeric_tokens = []

        for item in ocr_data:

            text = item["text"]

            # Only accept tokens which are primarily
            # numeric. This prevents random words from
            # becoming a number.

            digits = re.sub(
                r"\D",
                "",
                text
            )

            non_space = re.sub(
                r"[\s\-]",
                "",
                text
            )

            if (
                len(digits) >= 2
                and len(digits) >= len(non_space) * 0.6
            ):

                numeric_tokens.append(
                    item
                )

        # Sort by vertical position
        numeric_tokens.sort(
            key=lambda x:
            sum(p[1] for p in x["bbox"]) / 4
        )

        candidates = []

        # Look for combinations of 3 numeric tokens.
        for i in range(
            len(numeric_tokens)
        ):

            current = ""

            confidence_values = []

            for j in range(
                i,
                min(
                    i + 5,
                    len(numeric_tokens)
                )
            ):

                token = re.sub(
                    r"\D",
                    "",
                    numeric_tokens[j]["text"]
                )

                if not token:
                    continue

                current += token

                confidence_values.append(
                    numeric_tokens[j][
                        "confidence"
                    ]
                )

                if len(current) == 12:

                    confidence = (
                        sum(confidence_values)
                        /
                        len(confidence_values)
                    )

                    candidates.append({
                        "number": current,
                        "confidence": confidence
                    })

                    break

                if len(current) > 12:
                    break

        return candidates

    # ========================================================
    # FIND BEST AADHAAR NUMBER
    # ========================================================

    def find_aadhaar_number(
        self,
        ocr_data
    ):

        candidates = []

        # ----------------------------------------------------
        # Direct candidates
        # ----------------------------------------------------

        for item in ocr_data:

            found = self.extract_candidates(
                item["text"]
            )

            for number in found:

                candidates.append({
                    "number": number,
                    "confidence": item[
                        "confidence"
                    ],
                    "source": "direct"
                })

        # ----------------------------------------------------
        # Combined candidates
        # ----------------------------------------------------

        combined = self.combine_numeric_tokens(
            ocr_data
        )

        for candidate in combined:

            candidates.append({
                "number": candidate["number"],
                "confidence": candidate[
                    "confidence"
                ],
                "source": "combined"
            })

        if not candidates:
            return None

        # ----------------------------------------------------
        # Aggregate same candidate
        # ----------------------------------------------------

        scores = {}

        for candidate in candidates:

            number = candidate["number"]
            confidence = candidate[
                "confidence"
            ]

            score = confidence

            # Exact 12 digit number
            score += 0.10

            # Verhoeff bonus
            if self.verhoeff_validate(
                number
            ):
                score += 0.15

            # Multiple OCR passes finding
            # the same number is strong evidence.
            if number not in scores:

                scores[number] = {
                    "score": score,
                    "count": 1
                }

            else:

                scores[number]["count"] += 1

                scores[number]["score"] = max(
                    scores[number]["score"],
                    score
                )

        # Add agreement bonus
        for number in scores:

            scores[number]["score"] += (
                min(
                    scores[number]["count"],
                    5
                ) * 0.05
            )

        best = max(
            scores,
            key=lambda x:
            scores[x]["score"]
        )

        return {
            "number": best,
            "score": scores[best]["score"],
            "occurrences": scores[best][
                "count"
            ]
        }

    # ========================================================
    # VERHOEFF
    # ========================================================

    @staticmethod
    def verhoeff_validate(number):

        if (
            not number
            or not number.isdigit()
            or len(number) != 12
        ):
            return False

        checksum = 0

        for i, digit in enumerate(
            map(int, number[::-1])
        ):

            checksum = D_TABLE[
                checksum
            ][
                P_TABLE[
                    i % 8
                ][digit]
            ]

        return checksum == 0

    # ========================================================
    # PROCESS OCR
    # ========================================================

    def perform_ocr(
        self,
        image
    ):

        variants = self.create_variants(
            image
        )

        all_results = []

        for index, variant in enumerate(
            variants
        ):

            print(
                f"OCR pass {index + 1}/"
                f"{len(variants)}..."
            )

            # EasyOCR
            easy_results = self.easyocr(
                variant
            )

            all_results.extend(
                easy_results
            )

            # Tesseract fallback
            if TESSERACT_AVAILABLE:

                tess_results = self.tesseract(
                    variant
                )

                all_results.extend(
                    tess_results
                )

        return all_results

    # ========================================================
    # MAIN PROCESS
    # ========================================================

    def process(
        self,
        image_path
    ):

        image = self.load_image(
            image_path
        )

        print(
            "\nRunning multi-pass Aadhaar OCR..."
        )

        ocr_data = self.perform_ocr(
            image
        )

        result = self.find_aadhaar_number(
            ocr_data
        )

        # ----------------------------------------------------
        # NOTHING FOUND
        # ----------------------------------------------------

        if not result:

            return {
                "document_type": "AADHAAR",
                "status": "CLEARER IMAGE REQUIRED",
                "aadhaar_number": None,
                "masked_number": "NOT DETECTED",
                "ocr_confidence": 0,
                "format_valid": False,
                "checksum_valid": False,
                "reason": (
                    "No reliable 12-digit Aadhaar "
                    "number was detected."
                )
            }

        number = result[
            "number"
        ]

        confidence = min(
            result["score"],
            1.0
        )

        format_valid = (
            number.isdigit()
            and len(number) == 12
        )

        checksum_valid = (
            self.verhoeff_validate(
                number
            )
        )

        masked = (
            "XXXX XXXX "
            + number[-4:]
        )

        # ----------------------------------------------------
        # FINAL STATUS
        # ----------------------------------------------------

        if confidence < 0.40:

            status = (
                "AADHAAR DETECTED - "
                "LOW CONFIDENCE"
            )

            reason = (
                "A possible Aadhaar number was "
                "detected, but OCR confidence is low."
            )

        else:

            status = (
                "AADHAAR NUMBER DETECTED"
            )

            if checksum_valid:

                reason = (
                    "A 12-digit Aadhaar number was "
                    "detected and the extracted number "
                    "passed Verhoeff checksum validation."
                )

            else:

                reason = (
                    "A 12-digit Aadhaar number was "
                    "detected. The extracted number "
                    "did not pass checksum validation."
                )

        return {

            "document_type": "AADHAAR",

            "status": status,

            "aadhaar_number": number,

            "masked_number": masked,

            "ocr_confidence": round(
                confidence * 100,
                2
            ),

            "format_valid": format_valid,

            "checksum_valid": checksum_valid,

            "ocr_occurrences": result[
                "occurrences"
            ],

            "reason": reason
        }

    # ========================================================
    # PRINT RESULT
    # ========================================================

    @staticmethod
    def print_result(
        result
    ):

        print(
            "\n" + "=" * 60
        )

        print(
            "                 AADHAAR RESULT"
        )

        print(
            "=" * 60
        )

        print(
            f"STATUS      : "
            f"{result.get('status', 'UNKNOWN')}"
        )

        print(
            f"AADHAAR NO. : "
            f"{result.get('masked_number', 'NOT DETECTED')}"
        )

        print(
            f"OCR CONF.   : "
            f"{result.get('ocr_confidence', 0)}%"
        )

        print(
            f"FORMAT      : "
            f"{'PASS' if result.get('format_valid') else 'FAIL'}"
        )

        print(
            f"CHECKSUM    : "
            f"{'PASS' if result.get('checksum_valid') else 'FAIL'}"
        )

        if "ocr_occurrences" in result:

            print(
                f"OCR MATCHES : "
                f"{result['ocr_occurrences']}"
            )

        print(
            f"REASON      : "
            f"{result.get('reason', '')}"
        )

        print(
            "=" * 60
        )


if __name__ == "__main__":

    aadhaar = AadhaarOCR()

    result = aadhaar.process(
        "aadhaar.jpeg"
    )

    aadhaar.print_result(
        result
    )