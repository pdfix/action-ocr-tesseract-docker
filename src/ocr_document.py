import tempfile
from typing import BinaryIO, Optional, cast

import pytesseract
from pdfixsdk import (
    GetPdfix,
    PdfDoc,
    Pdfix,
    PdfPage,
    kSaveFull,
)
from tqdm import tqdm

from constants import (
    PERCENT_OCR,
    PERCENT_RENDER,
    PERCENT_XOBJECT,
    PROGRESS_FIRST_STEP,
    PROGRESS_SECOND_STEP,
    PROGRESS_THIRD_STEP,
)
from exceptions import (
    PdfixFailedToOcrException,
    PdfixFailedToOpenException,
    PdfixFailedToSaveException,
    PdfixInitializeException,
)
from ocr_base import OcrBase
from page_renderer import render_page
from utils_sdk import authorize_sdk


class OcrDocument(OcrBase):
    """Full-page OCR: render every page as-is, then embed invisible Tesseract text."""

    def ocr(self) -> None:
        """
        Run full-page OCR using Tesseract and place an invisible text Form XObject per page.
        """
        total_progress_count: int = PROGRESS_FIRST_STEP + PROGRESS_SECOND_STEP + PROGRESS_THIRD_STEP
        with tqdm(total=total_progress_count) as progress_bar:
            progress_bar.set_description("Initializing")

            print(f"Available config files: {pytesseract.get_languages(config='')}")

            pdfix: Optional[Pdfix] = GetPdfix()
            if pdfix is None:
                raise PdfixInitializeException()

            authorize_sdk(pdfix, self.license_name, self.license_key)

            doc: Optional[PdfDoc] = pdfix.OpenDoc(self.input_path, "")
            if doc is None:
                raise PdfixFailedToOpenException(pdfix, self.input_path)

            try:
                lang: str = self._resolve_lang(doc)
                print(f"Using language: {lang}")

                progress_bar.update(PROGRESS_FIRST_STEP)
                progress_bar.set_description("Processing pages")

                number_of_pages: int = doc.GetNumPages()
                step_count: float = float(PROGRESS_SECOND_STEP) / max(number_of_pages, 1)
                render_step_units: float = step_count * PERCENT_RENDER
                ocr_step_units: float = step_count * PERCENT_OCR
                xobject_step_units: float = step_count * PERCENT_XOBJECT

                for page_index in range(number_of_pages):
                    page: Optional[PdfPage] = doc.AcquirePage(page_index)
                    if page is None:
                        raise PdfixFailedToOcrException(pdfix, "Unable to acquire page")

                    try:
                        with tempfile.NamedTemporaryFile() as tmp:
                            render_page(pdfix, page, self.zoom, cast(BinaryIO, tmp.file))
                            progress_bar.update(render_step_units)

                            temp_pdf_page = pytesseract.image_to_pdf_or_hocr(
                                tmp.name + ".jpg",
                                extension="pdf",
                                lang=lang,
                            )
                            progress_bar.update(ocr_step_units)

                        self._place_ocr_form(pdfix, doc, page, temp_pdf_page)
                        progress_bar.update(xobject_step_units)
                    finally:
                        page.Release()

                progress_bar.n = PROGRESS_FIRST_STEP + PROGRESS_SECOND_STEP
                progress_bar.set_description("Saving document")
                progress_bar.refresh()

                if not doc.Save(self.output_path, kSaveFull):
                    raise PdfixFailedToSaveException(pdfix, self.output_path)

                progress_bar.n = total_progress_count
                progress_bar.set_description("Done")
                progress_bar.refresh()
            finally:
                doc.Close()

            pdfix.Destroy()
