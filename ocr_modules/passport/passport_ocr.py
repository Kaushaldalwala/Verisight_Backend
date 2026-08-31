"""
passport_ocr.py

Modular version of the Passport OCR notebook.

Extracts passport information from the MRZ using PassportEye and EasyOCR.
The implementation follows the logic of the supplied test_passport.ipynb.
"""

import json
import os
import string as st
import tempfile
from pathlib import Path

import cv2
import easyocr
import matplotlib.image as mpimg
from dateutil import parser
from passporteye import read_mrz


class PassportOCR:
    """Passport MRZ OCR extractor."""

    def __init__(self, country_codes_path=None, gpu=False, reader=None):
        """
        Initialize PassportOCR.

        Parameters
        ----------
        country_codes_path : str or Path, optional
            Path to country_codes.json. If omitted, the module's bundled
            country_codes.json is used.
        gpu : bool
            Whether EasyOCR should use GPU.
        reader : easyocr.Reader, optional
            Existing EasyOCR reader. Useful for reusing one reader.
        """
        self.reader = reader or easyocr.Reader(
            lang_list=["en"],
            gpu=gpu
        )

        if country_codes_path is None:
            country_codes_path = Path(__file__).with_name(
                "country_codes.json"
            )

        self.country_codes_path = Path(country_codes_path)

        if not self.country_codes_path.exists():
            raise FileNotFoundError(
                f"country_codes.json not found: {self.country_codes_path}"
            )

        with open(
            self.country_codes_path,
            "r",
            encoding="utf-8"
        ) as f:
            self.country_codes = json.load(f)

    @staticmethod
    def parse_date(value, iob=True):
        """Convert MRZ YYMMDD date to DD/MM/YYYY."""
        date = parser.parse(
            value,
            yearfirst=True
        ).date()
        return date.strftime("%d/%m/%Y")

    @staticmethod
    def clean(value):
        """Keep only alphanumeric characters and uppercase them."""
        return "".join(
            char for char in value
            if char.isalnum()
        ).upper()

    def get_country_name(self, country_code):
        """Convert an ISO alpha-3 country code to country name."""
        for country in self.country_codes:
            if country.get("alpha-3") == country_code:
                return country["name"].upper()

        return country_code

    @staticmethod
    def get_sex(code):
        """Convert MRZ sex code to M/F."""
        if code in ["M", "m", "F", "f"]:
            return code.upper()
        elif code == "0":
            return "M"
        else:
            return "F"

    @staticmethod
    def print_data(data):
        """Print extracted passport data in a readable format."""
        if not data:
            print("No passport data extracted.")
            return

        print("\n" + "=" * 55)
        print("             PASSPORT OCR RESULT")
        print("=" * 55)

        for key, value in data.items():
            info = key.replace("_", " ").capitalize()
            print(f"{info:<22}: {value}")

        print("=" * 55)

    def get_data(self, image_path):
        """
        Extract passport information from an image.

        Parameters
        ----------
        image_path : str or Path
            Full path to passport image.

        Returns
        -------
        dict or None
            Extracted passport information.
        """
        image_path = Path(image_path)

        if not image_path.exists():
            raise FileNotFoundError(
                f"Passport image not found: {image_path}"
            )

        mrz = read_mrz(
            str(image_path),
            save_roi=True
        )

        if not mrz:
            print(
                f"Machine cannot read image {image_path}."
            )
            return None

        roi = mrz.aux.get("roi")

        if roi is None:
            print("PassportEye detected MRZ but returned no ROI.")
            return None

        # Keep temporary ROI inside the system temp directory rather
        # than creating tmp.png in the project directory.
        with tempfile.NamedTemporaryFile(
            suffix=".png",
            delete=False
        ) as tmp:
            temp_path = tmp.name

        try:
            mpimg.imsave(
                temp_path,
                roi,
                cmap="gray"
            )

            img = cv2.imread(temp_path)

            if img is None:
                raise ValueError(
                    "Could not read the PassportEye MRZ ROI."
                )

            img = cv2.resize(
                img,
                (1110, 140)
            )

            allowlist = st.ascii_letters + st.digits + "< "

            code = self.reader.readtext(
                img,
                paragraph=False,
                detail=0,
                allowlist=allowlist
            )

            if len(code) < 2:
                print(
                    "MRZ OCR did not return two readable lines."
                )
                return None

            a = code[0].upper()
            b = code[1].upper()

            # MRZ standard uses 44 characters per line.
            a = a.ljust(44, "<")[:44]
            b = b.ljust(44, "<")[:44]

            surname_names = a[5:44].split(
                "<<",
                1
            )

            if len(surname_names) < 2:
                surname_names += [""]

            surname, names = surname_names

            user_info = {}

            user_info["name"] = (
                names.replace("<", " ")
                .strip()
                .upper()
            )

            user_info["surname"] = (
                surname.replace("<", " ")
                .strip()
                .upper()
            )

            user_info["sex"] = self.get_sex(
                self.clean(b[20])
            )

            user_info["date_of_birth"] = self.parse_date(
                b[13:19]
            )

            user_info["nationality"] = self.get_country_name(
                self.clean(b[10:13])
            )

            user_info["passport_type"] = self.clean(
                a[0:2]
            )

            user_info["passport_number"] = self.clean(
                b[0:9]
            )

            user_info["issuing_country"] = self.get_country_name(
                self.clean(a[2:5])
            )

            user_info["expiration_date"] = self.parse_date(
                b[21:27]
            )

            user_info["personal_number"] = self.clean(
                b[28:42]
            )

            return user_info

        finally:
            try:
                os.remove(temp_path)
            except OSError:
                pass
