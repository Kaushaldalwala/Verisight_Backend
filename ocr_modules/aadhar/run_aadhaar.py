
# from aadhaar_ocr import AadhaarOCR

# aadhaar = AadhaarOCR()
# result = aadhaar.process("images/aadhaar.jpg")
# aadhaar.print_result(result)

from pathlib import Path

from aadhaar_ocr import AadhaarOCR


BASE_DIR = Path(__file__).resolve().parent
# IMAGE_PATH = BASE_DIR / "aadhaar.jpg"
IMAGE_PATH = BASE_DIR / "aadhar_2.jpg"

# D:\hackathons\SIH-2026\OCR\ocr_modules\aadhar\


def main():
    print("=" * 60)
    print("AADHAAR OCR TEST")
    print("=" * 60)

    print(f"\nImage: {IMAGE_PATH}")

    if not IMAGE_PATH.exists():
        print("\nRESULT: IMAGE NOT FOUND")
        print(f"Expected image at: {IMAGE_PATH}")
        return

    try:
        print("\nInitializing Aadhaar OCR...")
        aadhaar = AadhaarOCR(gpu=False)

        print("Running OCR...\n")

        result = aadhaar.process(str(IMAGE_PATH))

        aadhaar.print_result(result)

    except Exception as e:
        print("\n" + "=" * 60)
        print("RESULT: ERROR")
        print("=" * 60)
        print(f"{type(e).__name__}: {e}")


if __name__ == "__main__":
    main()