import os
import tempfile
import uuid
from typing import Any, Optional

from pdfixsdk import (
    PdfDoc,
    Pdfix,
    PdfMatrix,
    PdfPage,
    PdfRect,
    PdsContent,
    PdsForm,
    PdsPageObject,
    PdsStream,
    kPdsPageText,
)

from exceptions import PdfixFailedToOcrException
from utils_sdk import (
    pdf_matrix_rotate,
    pdf_matrix_scale,
    pdf_matrix_translate,
    pi,
    translate_iso_to_tesseract,
)


class OcrBase:
    """Shared OCR plumbing: license, paths, and Tesseract PDF → Form XObject placement."""

    def __init__(
        self,
        license_name: str,
        license_key: str,
        input_path: str,
        output_path: str,
        lang: str,
        zoom: float,
    ) -> None:
        """
        Initialize shared OCR parameters.

        Args:
            license_name (str): Pdfix SDK license name (e-mail).
            license_key (str): Pdfix SDK license key.
            input_path (str): Path to the PDF document.
            output_path (str): Path to save the PDF document.
            lang (str): Tesseract language identifier (empty uses document lang).
            zoom (float): Zoom level for page rendering.
        """
        self.license_name: str = license_name
        self.license_key: str = license_key
        self.input_path: str = input_path
        self.output_path: str = output_path
        self.lang: str = lang
        self.zoom: float = zoom

    def _resolve_lang(self, doc: PdfDoc) -> str:
        """
        Resolve Tesseract language from constructor or document metadata.

        Args:
            doc (PdfDoc): Open document.

        Returns:
            Tesseract language identifier.
        """
        lang: str = self.lang
        if lang == "":
            pdf_lang = translate_iso_to_tesseract(doc.GetLang())
            lang = "eng" if pdf_lang is None else pdf_lang
        return lang

    def _place_ocr_form(self, pdfix: Pdfix, doc: PdfDoc, page: PdfPage, temp_pdf_page: bytes) -> None:
        """
        Import Tesseract PDF text into a Form XObject and place it on the page.

        This is the shared embed path used by full-page and content-filtered OCR.
        Future font / XObject optimizations should land here.

        Args:
            pdfix (Pdfix): Pdfix SDK instance.
            doc (PdfDoc): Destination document that owns the XObject.
            page (PdfPage): Target page.
            temp_pdf_page (bytes): PDF bytes returned by Tesseract.
        """
        xobj, temp_page_box = self._create_text_xobject_from_ocr(pdfix, doc, temp_pdf_page)
        self._add_xobject_to_page(pdfix, page, xobj, temp_page_box)

    def _create_text_xobject_from_ocr(
        self, pdfix: Pdfix, doc: PdfDoc, temp_pdf_page: bytes
    ) -> tuple[PdsStream, PdfRect]:
        """
        Open Tesseract PDF output, keep text objects only, create a Form XObject.

        Args:
            pdfix (Pdfix): Pdfix SDK instance.
            doc (PdfDoc): Destination document that owns the XObject.
            temp_pdf_page (bytes): PDF bytes returned by Tesseract.

        Returns:
            Tuple of (form XObject stream, Tesseract page crop box).
        """
        temp_path: str = f"{tempfile.gettempdir()}{str(uuid.uuid4())}.pdf"
        with open(temp_path, "w+b") as f:
            f.write(temp_pdf_page)

        try:
            temp_doc: Optional[PdfDoc] = pdfix.OpenDoc(temp_path, "")
            if temp_doc is None:
                raise PdfixFailedToOcrException(pdfix, "Unable to open OCR PDF")

            try:
                temp_page: Optional[PdfPage] = temp_doc.AcquirePage(0)
                if temp_page is None:
                    raise PdfixFailedToOcrException(pdfix, "Unable to acquire OCR page")

                try:
                    temp_page_box: PdfRect = temp_page.GetCropBox()

                    temp_page_content: Optional[PdsContent] = temp_page.GetContent()
                    if temp_page_content is None:
                        raise PdfixFailedToOcrException(pdfix, "Failed to obtain content from OCR page")

                    for j in reversed(range(temp_page_content.GetNumObjects())):
                        obj: Optional[PdsPageObject] = temp_page_content.GetObject(j)
                        if not obj:
                            continue
                        if obj.GetObjectType() != kPdsPageText:
                            temp_page_content.RemoveObject(obj)

                    temp_page.SetContent()

                    xobj: Optional[PdsStream] = doc.CreateXObjectFromPage(temp_page)
                    if xobj is None:
                        raise PdfixFailedToOcrException(pdfix, "Failed to create XObject from OCR page")

                    return xobj, temp_page_box
                finally:
                    temp_page.Release()
            finally:
                temp_doc.Close()
        finally:
            os.remove(temp_path)

    def _add_xobject_to_page(self, pdfix: Pdfix, page: PdfPage, xobj: PdsStream, temp_page_box: PdfRect) -> None:
        """
        Place the OCR Form XObject at the end of the page using the full-page matrix.

        Args:
            pdfix (Pdfix): Pdfix SDK instance.
            page (PdfPage): Target page.
            xobj (PdsStream): Form XObject from OCR.
            temp_page_box (PdfRect): Crop box of the Tesseract page.
        """
        crop_box: PdfRect = page.GetCropBox()
        rotate: float = page.GetRotate()

        width: int | Any = crop_box.right - crop_box.left
        width_tmp: int | Any = temp_page_box.right - temp_page_box.left
        height: int | Any = crop_box.top - crop_box.bottom
        height_tmp: int | Any = temp_page_box.top - temp_page_box.bottom

        if rotate == 90 or rotate == 270:
            width_tmp, height_tmp = height_tmp, width_tmp

        scale_x: float | Any = width / width_tmp
        scale_y: float | Any = height / height_tmp

        rotate_quads: float = (page.GetRotate() / 90) % 4
        matrix: PdfMatrix = PdfMatrix()
        matrix = pdf_matrix_rotate(matrix, rotate_quads * pi / 2, False)
        matrix = pdf_matrix_scale(matrix, scale_x, scale_y, False)
        if rotate_quads == 0:
            matrix = pdf_matrix_translate(matrix, crop_box.left, crop_box.bottom, False)
        elif rotate_quads == 1:
            matrix = pdf_matrix_translate(matrix, crop_box.right, crop_box.bottom, False)
        elif rotate_quads == 2:
            matrix = pdf_matrix_translate(matrix, crop_box.right, crop_box.top, False)
        elif rotate_quads == 3:
            matrix = pdf_matrix_translate(matrix, crop_box.left, crop_box.top, False)

        content: Optional[PdsContent] = page.GetContent()
        if content is None:
            raise PdfixFailedToOcrException(pdfix, "Failed to obtain content from page")

        form: Optional[PdsForm] = content.AddNewForm(-1, xobj, matrix)
        if form is None:
            raise PdfixFailedToOcrException(pdfix, "Failed to add XObject to page")
