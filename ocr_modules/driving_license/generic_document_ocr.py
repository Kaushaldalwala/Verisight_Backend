# import re
# from pathlib import Path
# from difflib import SequenceMatcher

# import cv2
# import easyocr


# class GenericDocumentOCR:
#     """
#     Layout-agnostic OCR module.

#     It does NOT assume a fixed document layout or predefined field list.
#     It detects text, attempts to identify label/value relationships, and
#     returns the fields actually found on the document.
#     """

#     def __init__(self, languages=None, gpu=False):
#         self.reader = easyocr.Reader(
#             languages or ["en"],
#             gpu=gpu
#         )

#     @staticmethod
#     def _center(bbox):
#         return (
#             sum(p[0] for p in bbox) / len(bbox),
#             sum(p[1] for p in bbox) / len(bbox),
#         )

#     @staticmethod
#     def _normalize(text):
#         return re.sub(r"\s+", " ", text or "").strip()

#     @staticmethod
#     def _clean_label(text):
#         text = re.sub(r"[:：]+$", "", text.strip())
#         return re.sub(r"\s+", " ", text)

#     @staticmethod
#     def _looks_like_label(text):
#         """
#         Heuristic only. No fixed document fields are assumed.
#         """
#         text = text.strip()

#         if not text or len(text) > 80:
#             return False

#         if ":" in text or "：" in text:
#             return True

#         words = text.split()
#         if len(words) <= 7 and not re.search(r"\d{4,}", text):
#             return True

#         return False

#     def load_image(self, image_path):
#         path = Path(image_path)

#         if not path.exists():
#             raise FileNotFoundError(
#                 f"Document image not found: {path}"
#             )

#         image = cv2.imread(str(path))

#         if image is None:
#             raise ValueError(
#                 f"Could not decode image: {path}"
#             )

#         return image

#     def preprocess(self, image):
#         gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

#         # Upscale small documents.
#         height, width = gray.shape[:2]
#         if width < 1600:
#             scale = 1600 / width
#             gray = cv2.resize(
#                 gray,
#                 None,
#                 fx=scale,
#                 fy=scale,
#                 interpolation=cv2.INTER_CUBIC
#             )

#         return gray

#     def ocr(self, image):
#         results = self.reader.readtext(
#             image,
#             paragraph=False,
#             detail=1
#         )

#         data = []

#         for bbox, text, confidence in results:
#             text = self._normalize(text)

#             if not text:
#                 continue

#             data.append({
#                 "text": text,
#                 "confidence": float(confidence),
#                 "bbox": bbox,
#                 "center": self._center(bbox)
#             })

#         data.sort(
#             key=lambda x: (
#                 x["center"][1],
#                 x["center"][0]
#             )
#         )

#         return data

#     def image_quality(self, ocr_data):
#         if not ocr_data:
#             return {
#                 "clear": False,
#                 "confidence": 0.0,
#                 "reason": "No readable text was detected."
#             }

#         average = sum(
#             item["confidence"]
#             for item in ocr_data
#         ) / len(ocr_data)

#         readable = sum(
#             item["confidence"] >= 0.50
#             for item in ocr_data
#         )

#         if average < 0.55:
#             return {
#                 "clear": False,
#                 "confidence": average,
#                 "reason": "OCR confidence is too low."
#             }

#         if readable < 2:
#             return {
#                 "clear": False,
#                 "confidence": average,
#                 "reason": "Insufficient readable text was detected."
#             }

#         return {
#             "clear": True,
#             "confidence": average,
#             "reason": "Sufficient text was detected."
#         }

#     def extract_dynamic_fields(self, ocr_data):
#         """
#         Attempts to infer key/value pairs without knowing the document
#         schema in advance.

#         Supported patterns:
#           Label: Value
#           Label - Value
#           Label     Value
#           Label on one line followed by value on the next line
#         """

#         fields = {}
#         used = set()

#         # Pattern 1: explicit separators.
#         for i, item in enumerate(ocr_data):
#             text = item["text"]

#             match = re.match(
#                 r"^\s*([^:：\-]{1,70})\s*[:：\-]\s*(.+?)\s*$",
#                 text
#             )

#             if match:
#                 label = self._clean_label(match.group(1))
#                 value = self._normalize(match.group(2))

#                 if label and value:
#                     fields[label] = {
#                         "value": value,
#                         "confidence": round(
#                             item["confidence"], 3
#                         ),
#                         "source": "same_line"
#                     }
#                     used.add(i)

#         # Pattern 2: label/value using nearby OCR boxes.
#         for i, label_item in enumerate(ocr_data):
#             if i in used:
#                 continue

#             label = self._clean_label(label_item["text"])

#             if not self._looks_like_label(label):
#                 continue

#             lx, ly = label_item["center"]

#             candidates = []

#             for j, value_item in enumerate(ocr_data):
#                 if i == j or j in used:
#                     continue

#                 vx, vy = value_item["center"]

#                 # Prefer values on the same row and to the right.
#                 horizontal = vx > lx
#                 vertical_gap = abs(vy - ly)

#                 if horizontal and vertical_gap < 45:
#                     distance = (
#                         (vx - lx) +
#                         vertical_gap * 2
#                     )

#                     candidates.append(
#                         (distance, j, value_item)
#                     )

#             # If no value is to the right, check the next line.
#             if not candidates:
#                 for j, value_item in enumerate(ocr_data):
#                     if i == j or j in used:
#                         continue

#                     vx, vy = value_item["center"]
#                     vertical_gap = vy - ly

#                     if 0 < vertical_gap < 80:
#                         candidates.append(
#                             (vertical_gap, j, value_item)
#                         )

#             if candidates:
#                 candidates.sort(key=lambda x: x[0])
#                 _, j, value_item = candidates[0]

#                 # Avoid pairing a likely label with another likely label.
#                 if not self._looks_like_label(
#                     value_item["text"]
#                 ):
#                     fields[label] = {
#                         "value": value_item["text"],
#                         "confidence": round(
#                             min(
#                                 label_item["confidence"],
#                                 value_item["confidence"]
#                             ),
#                             3
#                         ),
#                         "source": "layout_relation"
#                     }
#                     used.add(i)
#                     used.add(j)

#         return fields

#     def extract_unpaired_text(self, ocr_data, fields):
#         """
#         Keeps useful OCR text that could not confidently be assigned
#         to a field. This prevents silently throwing away information.
#         """
#         assigned = set()

#         for field in fields.values():
#             assigned.add(field["value"])

#         return [
#             {
#                 "text": item["text"],
#                 "confidence": round(
#                     item["confidence"], 3
#                 )
#             }
#             for item in ocr_data
#             if item["text"] not in assigned
#         ]

#     def process(self, image_path):
#         image = self.load_image(image_path)
#         processed = self.preprocess(image)

#         ocr_data = self.ocr(processed)
#         quality = self.image_quality(ocr_data)

#         if not quality["clear"]:
#             return {
#                 "document_type": self.document_type,
#                 "status": "CLEARER IMAGE REQUIRED",
#                 "ocr_confidence": round(
#                     quality["confidence"] * 100, 2
#                 ),
#                 "reason": quality["reason"],
#                 "fields": {},
#                 "unpaired_text": []
#             }

#         fields = self.extract_dynamic_fields(ocr_data)
#         unpaired = self.extract_unpaired_text(
#             ocr_data,
#             fields
#         )

#         if not fields:
#             status = "REVIEW REQUIRED"
#             reason = (
#                 "Text was detected, but no reliable "
#                 "key-value relationships were identified."
#             )
#         else:
#             status = "OCR COMPLETED"
#             reason = (
#                 "Text was extracted using layout-agnostic "
#                 "OCR and dynamic field detection."
#             )

#         return {
#             "document_type": self.document_type,
#             "status": status,
#             "ocr_confidence": round(
#                 quality["confidence"] * 100, 2
#             ),
#             "reason": reason,
#             "fields": fields,
#             "unpaired_text": unpaired,
#             "raw_ocr": [
#                 {
#                     "text": item["text"],
#                     "confidence": round(
#                         item["confidence"], 3
#                     )
#                 }
#                 for item in ocr_data
#             ]
#         }

#     @staticmethod
#     def print_result(result):
#         print("\n" + "=" * 65)
#         print(
#             f"{result.get('document_type', 'DOCUMENT')} OCR RESULT"
#         )
#         print("=" * 65)

#         print(
#             f"STATUS       : "
#             f"{result.get('status', 'UNKNOWN')}"
#         )

#         print(
#             f"OCR CONF.    : "
#             f"{result.get('ocr_confidence', 0)}%"
#         )

#         print(
#             f"REASON       : "
#             f"{result.get('reason', '')}"
#         )

#         print("\nEXTRACTED FIELDS")
#         print("-" * 65)

#         fields = result.get("fields", {})

#         if fields:
#             for label, data in fields.items():
#                 print(
#                     f"{label:<25} : "
#                     f"{data['value']} "
#                     f"(confidence: {data['confidence']})"
#                 )
#         else:
#             print("No reliable fields detected.")

#         unpaired = result.get("unpaired_text", [])

#         if unpaired:
#             print("\nOTHER DETECTED TEXT")
#             print("-" * 65)

#             for item in unpaired:
#                 print(
#                     f"{item['text']} "
#                     f"(confidence: {item['confidence']})"
#                 )

#         print("=" * 65)







import re
from pathlib import Path
from difflib import SequenceMatcher

import cv2
import easyocr


class GenericDocumentOCR:
    """
    Layout-agnostic OCR engine.

    Designed for documents where:
    - labels may be OCR'd incorrectly
    - values may appear beside or below labels
    - layouts can vary
    - useful text should not be discarded

    No fixed document schema is required.
    """

    def __init__(self, languages=None, gpu=False):
        self.reader = easyocr.Reader(
            languages or ["en"],
            gpu=gpu
        )

    # ---------------------------------------------------------
    # GEOMETRY
    # ---------------------------------------------------------

    @staticmethod
    def _center(bbox):
        return (
            sum(p[0] for p in bbox) / len(bbox),
            sum(p[1] for p in bbox) / len(bbox)
        )

    # ---------------------------------------------------------
    # TEXT NORMALIZATION
    # ---------------------------------------------------------

    @staticmethod
    def _normalize(text):
        if not text:
            return ""

        return re.sub(
            r"\s+",
            " ",
            text.strip()
        )

    @staticmethod
    def _alphanumeric(text):
        return re.sub(
            r"[^A-Z0-9]",
            "",
            text.upper()
        )

    @staticmethod
    def _clean_label(text):
        text = text.strip()

        text = re.sub(
            r"[:：]+$",
            "",
            text
        )

        return re.sub(
            r"\s+",
            " ",
            text
        )

    # ---------------------------------------------------------
    # FUZZY MATCHING
    # ---------------------------------------------------------

    @staticmethod
    def similarity(a, b):

        a = re.sub(
            r"[^A-Z0-9]",
            "",
            a.upper()
        )

        b = re.sub(
            r"[^A-Z0-9]",
            "",
            b.upper()
        )

        if not a or not b:
            return 0.0

        return SequenceMatcher(
            None,
            a,
            b
        ).ratio()

    def looks_like_known_label(self, text):

        """
        Fuzzy recognition of common document labels.

        This is NOT used to force a document schema.
        It only helps correct OCR errors in labels.
        """

        labels = [
            "NAME",
            "SURNAME",
            "GIVEN NAME",
            "DATE OF BIRTH",
            "DATE OF ISSUE",
            "DATE OF EXPIRY",
            "EXPIRY DATE",
            "EXPIRATION DATE",
            "BLOOD GROUP",
            "BLOOD TYPE",
            "ADDRESS",
            "FATHER NAME",
            "MOTHER NAME",
            "HUSBAND NAME",
            "WIFE NAME",
            "SON OF",
            "DAUGHTER OF",
            "WIFE OF",
            "LICENSE NUMBER",
            "LICENCE NUMBER",
            "DRIVING LICENSE",
            "DRIVING LICENCE",
            "DL NUMBER",
            "DOB",
            "VALID FROM",
            "VALID UNTIL",
            "ISSUED",
            "ISSUE DATE",
            "SEX",
            "GENDER",
        ]

        best_label = None
        best_score = 0

        for label in labels:

            score = self.similarity(
                text,
                label
            )

            if score > best_score:
                best_score = score
                best_label = label

        if best_score >= 0.65:

            return {
                "label": best_label,
                "score": best_score
            }

        return None

    # ---------------------------------------------------------
    # IMAGE
    # ---------------------------------------------------------

    def load_image(self, image_path):

        path = Path(image_path)

        if not path.exists():

            raise FileNotFoundError(
                f"Document image not found: {path}"
            )

        image = cv2.imread(
            str(path)
        )

        if image is None:

            raise ValueError(
                f"Could not decode image: {path}"
            )

        return image

    # ---------------------------------------------------------
    # PREPROCESSING
    # ---------------------------------------------------------

    def preprocess(self, image):

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY
        )

        height, width = gray.shape[:2]

        # Upscale small documents.
        if width < 1800:

            scale = 1800 / width

            gray = cv2.resize(
                gray,
                None,
                fx=scale,
                fy=scale,
                interpolation=cv2.INTER_CUBIC
            )

        # Improve local contrast.
        clahe = cv2.createCLAHE(
            clipLimit=2.0,
            tileGridSize=(8, 8)
        )

        gray = clahe.apply(gray)

        return gray

    # ---------------------------------------------------------
    # OCR
    # ---------------------------------------------------------

    def ocr(self, image):

        results = self.reader.readtext(
            image,
            paragraph=False,
            detail=1
        )

        data = []

        for bbox, text, confidence in results:

            text = self._normalize(
                text
            )

            if not text:
                continue

            center = self._center(
                bbox
            )

            data.append({

                "text": text,

                "confidence": float(
                    confidence
                ),

                "bbox": bbox,

                "center": center
            })

        data.sort(
            key=lambda x: (
                x["center"][1],
                x["center"][0]
            )
        )

        return data

    # ---------------------------------------------------------
    # IMAGE QUALITY
    # ---------------------------------------------------------

    def image_quality(
        self,
        ocr_data
    ):

        if not ocr_data:

            return {
                "clear": False,
                "confidence": 0.0,
                "reason":
                    "No readable text was detected."
            }

        average = sum(
            x["confidence"]
            for x in ocr_data
        ) / len(ocr_data)

        readable = sum(
            x["confidence"] >= 0.35
            for x in ocr_data
        )

        if readable < 3:

            return {
                "clear": False,
                "confidence": average,
                "reason":
                    "Insufficient readable text was detected."
            }

        return {
            "clear": True,
            "confidence": average,
            "reason":
                "Sufficient text was detected."
        }

    # ---------------------------------------------------------
    # DATE DETECTION
    # ---------------------------------------------------------

    @staticmethod
    def extract_dates(text):

        patterns = [

            r"\b\d{2}[/-]\d{2}[/-]\d{4}\b",

            r"\b\d{2}[/-]\d{2}[/-]\d{2}\b",

            r"\b\d{4}[/-]\d{2}[/-]\d{2}\b",

        ]

        dates = []

        for pattern in patterns:

            dates.extend(
                re.findall(
                    pattern,
                    text
                )
            )

        return dates

    # ---------------------------------------------------------
    # NUMBER DETECTION
    # ---------------------------------------------------------

    @staticmethod
    def extract_numbers(text):

        return re.findall(
            r"\b\d{5,20}\b",
            text
        )

    # ---------------------------------------------------------
    # DYNAMIC FIELD EXTRACTION
    # ---------------------------------------------------------

    def extract_dynamic_fields(
        self,
        ocr_data
    ):

        fields = {}

        used = set()

        # -------------------------------------------------
        # PASS 1
        # Explicit Label : Value
        # -------------------------------------------------

        for i, item in enumerate(ocr_data):

            text = item["text"]

            match = re.match(
                r"^\s*(.{1,70}?)"
                r"\s*[:：\-]\s*(.+?)\s*$",
                text
            )

            if match:

                label = self._clean_label(
                    match.group(1)
                )

                value = self._normalize(
                    match.group(2)
                )

                if label and value:

                    fields[label] = {

                        "value": value,

                        "confidence":
                            round(
                                item["confidence"],
                                3
                            ),

                        "source":
                            "same_line"
                    }

                    used.add(i)

        # -------------------------------------------------
        # PASS 2
        # Fuzzy labels + spatial values
        # -------------------------------------------------

        for i, label_item in enumerate(
            ocr_data
        ):

            if i in used:
                continue

            raw_label = label_item["text"]

            fuzzy = self.looks_like_known_label(
                raw_label
            )

            if not fuzzy:
                continue

            normalized_label = fuzzy["label"]

            lx, ly = label_item["center"]

            candidates = []

            for j, value_item in enumerate(
                ocr_data
            ):

                if i == j or j in used:
                    continue

                vx, vy = value_item["center"]

                horizontal_distance = vx - lx

                vertical_distance = abs(
                    vy - ly
                )

                # Same row.
                if (
                    horizontal_distance > 0
                    and vertical_distance < 70
                ):

                    distance = (
                        horizontal_distance
                        + vertical_distance * 2
                    )

                    candidates.append(
                        (
                            distance,
                            j,
                            value_item
                        )
                    )

                # Value below label.
                elif (
                    0 < vy - ly < 120
                    and abs(vx - lx) < 350
                ):

                    distance = (
                        (vy - ly) * 2
                        + abs(vx - lx)
                    )

                    candidates.append(
                        (
                            distance,
                            j,
                            value_item
                        )
                    )

            if candidates:

                candidates.sort(
                    key=lambda x: x[0]
                )

                _, j, value_item = candidates[0]

                fields[normalized_label] = {

                    "value":
                        value_item["text"],

                    "confidence":
                        round(
                            min(
                                label_item[
                                    "confidence"
                                ],
                                value_item[
                                    "confidence"
                                ]
                            ),
                            3
                        ),

                    "source":
                        "fuzzy_label_layout",

                    "label_ocr":
                        raw_label,

                    "label_similarity":
                        round(
                            fuzzy["score"],
                            3
                        )
                }

                used.add(i)
                used.add(j)

        # -------------------------------------------------
        # PASS 3
        # Automatically detect dates
        # -------------------------------------------------

        date_counter = 1

        for item in ocr_data:

            dates = self.extract_dates(
                item["text"]
            )

            for date in dates:

                key = f"Detected Date {date_counter}"

                fields[key] = {

                    "value": date,

                    "confidence":
                        round(
                            item["confidence"],
                            3
                        ),

                    "source":
                        "pattern_detection"
                }

                date_counter += 1

        # -------------------------------------------------
        # PASS 4
        # Automatically detect long numbers
        # -------------------------------------------------

        number_counter = 1

        for item in ocr_data:

            numbers = self.extract_numbers(
                item["text"]
            )

            for number in numbers:

                key = (
                    f"Detected Number "
                    f"{number_counter}"
                )

                fields[key] = {

                    "value": number,

                    "confidence":
                        round(
                            item["confidence"],
                            3
                        ),

                    "source":
                        "pattern_detection"
                }

                number_counter += 1

        return fields

    # ---------------------------------------------------------
    # UNPAIRED TEXT
    # ---------------------------------------------------------

    def extract_unpaired_text(
        self,
        ocr_data,
        fields
    ):

        assigned = set()

        for field in fields.values():

            assigned.add(
                field["value"]
            )

        return [

            {
                "text":
                    item["text"],

                "confidence":
                    round(
                        item["confidence"],
                        3
                    )
            }

            for item in ocr_data

            if item["text"]
            not in assigned
        ]

    # ---------------------------------------------------------
    # MAIN PROCESS
    # ---------------------------------------------------------

    def process(
        self,
        image_path
    ):

        image = self.load_image(
            image_path
        )

        processed = self.preprocess(
            image
        )

        ocr_data = self.ocr(
            processed
        )

        quality = self.image_quality(
            ocr_data
        )

        if not quality["clear"]:

            return {

                "document_type":
                    self.document_type,

                "status":
                    "CLEARER IMAGE REQUIRED",

                "ocr_confidence":
                    round(
                        quality["confidence"]
                        * 100,
                        2
                    ),

                "reason":
                    quality["reason"],

                "fields": {},

                "unpaired_text": []
            }

        fields = self.extract_dynamic_fields(
            ocr_data
        )

        unpaired = self.extract_unpaired_text(
            ocr_data,
            fields
        )

        if not fields:

            status = "REVIEW REQUIRED"

            reason = (
                "Text was detected, but "
                "no reliable fields could "
                "be identified."
            )

        else:

            status = "OCR COMPLETED"

            reason = (
                "Text and document information "
                "were extracted using OCR, "
                "fuzzy label matching, "
                "spatial relationships and "
                "pattern detection."
            )

        return {

            "document_type":
                self.document_type,

            "status":
                status,

            "ocr_confidence":
                round(
                    quality["confidence"]
                    * 100,
                    2
                ),

            "reason":
                reason,

            "fields":
                fields,

            "unpaired_text":
                unpaired,

            "raw_ocr":

                [
                    {

                        "text":
                            item["text"],

                        "confidence":
                            round(
                                item["confidence"],
                                3
                            )
                    }

                    for item in ocr_data
                ]
        }

    # ---------------------------------------------------------
    # PRINT
    # ---------------------------------------------------------

    @staticmethod
    def print_result(result):

        print("\n" + "=" * 65)

        print(
            f"{result.get(
                'document_type',
                'DOCUMENT'
            )} OCR RESULT"
        )

        print("=" * 65)

        print(
            f"STATUS       : "
            f"{result.get(
                'status',
                'UNKNOWN'
            )}"
        )

        print(
            f"OCR CONF.    : "
            f"{result.get(
                'ocr_confidence',
                0
            )}%"
        )

        print(
            f"REASON       : "
            f"{result.get(
                'reason',
                ''
            )}"
        )

        print("\nEXTRACTED FIELDS")

        print("-" * 65)

        fields = result.get(
            "fields",
            {}
        )

        if fields:

            for label, data in fields.items():

                print(
                    f"{label:<30} : "
                    f"{data['value']} "
                    f"(confidence: "
                    f"{data['confidence']})"
                )

        else:

            print(
                "No reliable fields detected."
            )

        print("\nOTHER DETECTED TEXT")

        print("-" * 65)

        for item in result.get(
            "unpaired_text",
            []
        ):

            print(
                f"{item['text']} "
                f"(confidence: "
                f"{item['confidence']})"
            )

        print("=" * 65)