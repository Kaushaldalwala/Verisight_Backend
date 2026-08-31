from .generic_document_ocr import GenericDocumentOCR


class NationalIDOCR(GenericDocumentOCR):
    """
    Generic NATIONAL ID OCR.

    No country-specific field schema or fixed document layout is assumed.
    """

    document_type = "NATIONAL ID"
