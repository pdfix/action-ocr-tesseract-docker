import tempfile

import pytesseract
from pdfixsdk import (
    PdfImageParams,
    Pdfix,
    PdfPage,
    PdfPageRenderParams,
    kImageDIBFormatArgb,
    kImageFormatJpg,
    kPsTruncate,
    kRotate0,
)

from exceptions import PdfixException


def render_pages(page: PdfPage, pdfix: Pdfix, lang: str) -> bytes:
    """
    Render a PDF page into a temporary file, which is then used for OCR.

    Args:
        page (PdfPage): The PDF page to be processed for OCR.
        pdfix (Pdfix): The Pdfix SDK object.
        lang (str): The language identifier for OCR.

    Returns:
        Raw PDF bytes.
    """
    zoom = 2.0
    page_view = page.AcquirePageView(zoom, kRotate0)
    if page_view is None:
        raise PdfixException("Unable to acquire page view")

    width = page_view.GetDeviceWidth()
    height = page_view.GetDeviceHeight()
    # Create an image
    image = pdfix.CreateImage(width, height, kImageDIBFormatArgb)
    if image is None:
        raise PdfixException("Unable to create image")

    # Render page
    render_params = PdfPageRenderParams()
    render_params.image = image
    render_params.matrix = page_view.GetDeviceMatrix()
    if not page.DrawContent(render_params):
        raise PdfixException("Unable to draw content")

    # Create temp file for rendering
    with tempfile.NamedTemporaryFile() as tmp:
        # Save image to file
        stm = pdfix.CreateFileStream(tmp.name + ".jpg", kPsTruncate)
        if stm is None:
            raise PdfixException("Unable to create file stream")

        img_params = PdfImageParams()
        img_params.format = kImageFormatJpg
        img_params.quality = 100
        if not image.SaveToStream(stm, img_params):
            raise PdfixException("Unable to save image to stream")

        return pytesseract.image_to_pdf_or_hocr(
            tmp.name + ".jpg",
            extension="pdf",
            lang=lang,
        )
