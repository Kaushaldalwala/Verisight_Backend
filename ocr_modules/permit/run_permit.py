from permit_ocr import PermitOCR

# Change this path to your document image.
IMAGE_PATH = r"D:/hackathons/SIH-2026/OCR/images/document.jpg"

ocr = PermitOCR()
result = ocr.process(IMAGE_PATH)

ocr.print_result(result)
