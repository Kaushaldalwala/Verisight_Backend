from .generic_document_ocr import GenericDocumentOCR


class PermitOCR(GenericDocumentOCR):
    """
    Generic PERMIT OCR.

    No country-specific field schema or fixed document layout is assumed.
    """

    document_type = "PERMIT"
