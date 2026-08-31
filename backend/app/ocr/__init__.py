"""
OCR wrappers package.

Each submodule provides a single `process(image_path: str) -> dict` function
that wraps the corresponding class in ocr_modules/.

Readers are initialized as singletons (lazy, on first call) so EasyOCR models
are loaded only once per server process, not on every request.
"""
