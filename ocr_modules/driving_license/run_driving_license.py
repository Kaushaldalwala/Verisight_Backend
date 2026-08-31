from driving_license_ocr import DrivingLicenseOCR


IMAGE_PATH = (
    r"D:\hackathons\SIH-2026\OCR\ocr_modules"
    r".\driving_license\driving_license.jpg"
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