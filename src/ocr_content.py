import logging
import tempfile
from pathlib import Path
from typing import BinaryIO, Optional, cast

import pytesseract
from pdfixsdk import (
    GetPdfix,
    PdfDoc,
    Pdfix,
    PdfPage,
    PdfPageObjectEnumProcType,
    PdfTemplateQuery,
    PdsContent,
    PdsPageObject,
    PsFileStream,
    kDataFormatJson,
    kEnumForms,
    kEnumResultContinue,
    kPsReadOnly,
    kSaveFull,
    kStateDefault,
    kStateNoRender,
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
    PdfixFailedToLoadTemplateException,
    PdfixFailedToOcrException,
    PdfixFailedToOpenException,
    PdfixFailedToSaveException,
    PdfixInitializeException,
)
from logger import get_logger
from ocr_base import OcrBase
from page_renderer import render_page
from utils_sdk import authorize_sdk

logger: logging.Logger = get_logger("app_logger")


class OcrContent(OcrBase):
    def __init__(
        self,
        license_name: str,
        license_key: str,
        input_path: str,
        output_path: str,
        regex_template: str | Path,
        lang: str,
        zoom: float,
    ) -> None:
        """
        Initialize OCR for filtered page content in a PDF document.

        Args:
            license_name (str): Pdfix SDK license name (e-mail).
            license_key (str): Pdfix SDK license key.
            input_path (str): Path to the PDF document.
            output_path (str): Path to save the PDF document.
            regex_template (str | Path): Regex or path to a template JSON file.
            lang (str): Tesseract language identifier (empty uses document lang).
            zoom (float): Zoom level for page rendering.
        """
        super().__init__(license_name, license_key, input_path, output_path, lang, zoom)
        self.regex_template: str | Path = regex_template

        self.document: Optional[PdfDoc] = None
        self.template_query: Optional[PdfTemplateQuery] = None
        self._hit_ptrs: set[int] = set()

    def ocr_content(self) -> None:
        """
        OCR filtered page content and place an invisible text Form XObject per page.
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

                template_query: Optional[PdfTemplateQuery] = self._create_template_query(pdfix, doc)
                self.document = doc
                self.template_query = template_query

                progress_bar.update(PROGRESS_FIRST_STEP)
                progress_bar.set_description("Processing pages")

                number_of_pages: int = doc.GetNumPages()
                step_count: float = float(PROGRESS_SECOND_STEP) / max(number_of_pages, 1)
                render_step_units: float = step_count * PERCENT_RENDER
                ocr_step_units: float = step_count * PERCENT_OCR
                xobject_step_units: float = step_count * PERCENT_XOBJECT

                try:
                    for page_index in range(number_of_pages):
                        page: Optional[PdfPage] = doc.AcquirePage(page_index)
                        if page is None:
                            raise PdfixFailedToOcrException(pdfix, "Unable to acquire page")

                        try:
                            hits: list[int] = self._collect_hits(doc, page)
                            if not hits:
                                progress_bar.update(step_count)
                                continue

                            self._set_hit_render_flags(doc, page, hits)
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
                                self._reset_render_flags(doc, page)
                        finally:
                            page.Release()
                finally:
                    self.document = None
                    self.template_query = None

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

    def _create_template_query(self, pdfix: Pdfix, doc: PdfDoc) -> PdfTemplateQuery:
        """
        Create and load a template query from regex or JSON template file.

        Args:
            pdfix (Pdfix): Pdfix SDK instance.
            doc (PdfDoc): Open document.

        Returns:
            Loaded PdfTemplateQuery.
        """
        template_query: Optional[PdfTemplateQuery] = doc.CreateTemplateQuery()
        if template_query is None:
            raise PdfixFailedToLoadTemplateException(pdfix, "Failed to create Template query")

        if isinstance(self.regex_template, str):
            if not template_query.LoadFromRegex(self.regex_template):
                raise PdfixFailedToLoadTemplateException(pdfix, "Failed to load template from regex")
        else:
            stream: Optional[PsFileStream] = pdfix.CreateFileStream(str(self.regex_template), kPsReadOnly)
            if stream is None:
                raise PdfixFailedToLoadTemplateException(pdfix, "Failed to create file stream for template")
            if not template_query.LoadFromStream(stream, kDataFormatJson):
                raise PdfixFailedToLoadTemplateException(pdfix, "Failed to load template from stream")

        return template_query

    def _collect_hits(self, doc: PdfDoc, page: PdfPage) -> list[int]:
        """
        Enumerate page objects and collect pointers that match the template query.

        Args:
            doc (PdfDoc): Open document.
            page (PdfPage): Page to enumerate.

        Returns:
            List of matching page-object pointers.
        """
        content: Optional[PdsContent] = page.GetContent()
        if content is None:
            return []

        hits: list[int] = []
        self._hit_ptrs = set()

        def enum_proc(page_object_ptr: int, index: int, client_data: int) -> int:
            page_object: PdsPageObject = PdsPageObject(page_object_ptr)
            if self.template_query is None:
                logger.error("Template query is not initialized")
                return kEnumResultContinue
            if self.template_query.TestPageObject(page_object):
                hits.append(page_object_ptr)
                self._hit_ptrs.add(page_object_ptr)
            return kEnumResultContinue

        page_object_enum_proc = PdfPageObjectEnumProcType(enum_proc)
        doc.EnumPageObjects(content, None, kEnumForms, page_object_enum_proc, None)
        return hits

    def _set_hit_render_flags(self, doc: PdfDoc, page: PdfPage, hits: list[int]) -> None:
        """
        Enable rendering only for collected hits; disable all other page objects.

        Args:
            doc (PdfDoc): Open document.
            page (PdfPage): Page whose objects are marked.
            hits (list[int]): Matching page-object pointers.
        """
        self._hit_ptrs = set(hits)
        content: Optional[PdsContent] = page.GetContent()
        if content is None:
            return

        def enum_proc(page_object_ptr: int, index: int, client_data: int) -> int:
            page_object: PdsPageObject = PdsPageObject(page_object_ptr)
            if page_object_ptr in self._hit_ptrs:
                page_object.SetStateFlags(kStateDefault)
            else:
                page_object.SetStateFlags(kStateNoRender)
            return kEnumResultContinue

        page_object_enum_proc = PdfPageObjectEnumProcType(enum_proc)
        doc.EnumPageObjects(content, None, kEnumForms, page_object_enum_proc, None)

    def _reset_render_flags(self, doc: PdfDoc, page: PdfPage) -> None:
        """
        Reset all page objects to the default render state.

        Args:
            doc (PdfDoc): Open document.
            page (PdfPage): Page whose objects are reset.
        """
        content: Optional[PdsContent] = page.GetContent()
        if content is None:
            return

        def enum_proc(page_object_ptr: int, index: int, client_data: int) -> int:
            page_object: PdsPageObject = PdsPageObject(page_object_ptr)
            page_object.SetStateFlags(kStateDefault)
            return kEnumResultContinue

        page_object_enum_proc = PdfPageObjectEnumProcType(enum_proc)
        doc.EnumPageObjects(content, None, kEnumForms, page_object_enum_proc, None)
