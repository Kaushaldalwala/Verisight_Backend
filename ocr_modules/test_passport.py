from pathlib import Path

from passport.passport_ocr import PassportOCR


# Current module directory
BASE_DIR = Path(__file__).resolve().parent

# Passport test image
IMAGE_PATH = BASE_DIR / "passport" / "passport.png"


def main():
    print("=" * 60)
    print("PASSPORT OCR TEST")
    print("=" * 60)

    print(f"\nImage: {IMAGE_PATH}")

    if not IMAGE_PATH.exists():
        print("\nERROR: Passport image not found.")
        return

    try:
        print("\nInitializing Passport OCR...")
        ocr = PassportOCR(gpu=False)

        print("Running OCR...\n")
        result = ocr.get_data(IMAGE_PATH)

        if result is None:
            print("=" * 60)
            print("RESULT: OCR FAILED")
            print("=" * 60)
            print("The passport image could not be read.")
            return

        ocr.print_data(result)

        print("\nRESULT: OCR SUCCESS")

    except Exception as e:
        print("\n" + "=" * 60)
        print("RESULT: ERROR")
        print("=" * 60)
        print(f"{type(e).__name__}: {e}")


if __name__ == "__main__":
    main()