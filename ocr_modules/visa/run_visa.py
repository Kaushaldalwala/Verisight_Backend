from pathlib import Path

from visa_ocr import VisaOCR


BASE_DIR = Path(__file__).resolve().parent
IMAGE_PATH = BASE_DIR / "visa_1.jpg"


def main():
    print("=" * 60)
    print("VISA OCR TEST")
    print("=" * 60)

    print(f"\nImage: {IMAGE_PATH}")

    if not IMAGE_PATH.exists():
        print("\nRESULT: IMAGE NOT FOUND")
        print(f"Expected image at: {IMAGE_PATH}")
        return

    try:
        print("\nInitializing Visa OCR...")
        visa = VisaOCR(gpu=False)

        print("Running OCR...\n")

        result = visa.process(str(IMAGE_PATH))

        visa.print_result(result)

    except Exception as e:
        print("\n" + "=" * 60)
        print("RESULT: ERROR")
        print("=" * 60)
        print(f"{type(e).__name__}: {e}")


if __name__ == "__main__":
    main()