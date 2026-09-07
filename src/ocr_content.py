import logging
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any, BinaryIO, Optional, cast

import pytesseract
from pdfixsdk import (
    GetPdfix,
    PdfDoc,
    Pdfix,
    PdfMatrix,
    PdfPage,
    PdfPageObjectEnumProcType,
    PdfRect,
    PdfTemplateQuery,
    PdsContent,
    PdsForm,
    PdsPageObject,
    PdsStream,
    PsFileStream,
    kDataFormatJson,
    kEnumForms,
    kEnumResultContinue,
    kPdsPageText,
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
from page_renderer import render_page
from utils_sdk import (
    authorize_sdk,
    pdf_matrix_rotate,
    pdf_matrix_scale,
    pdf_matrix_translate,
    pi,
    translate_iso_to_tesseract,
)

logger: logging.Logger = get_logger("app_logger")


class OcrContent:
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
        self.license_name: str = license_name
        self.license_key: str = license_key
        self.input_path: str = input_path
        self.output_path: str = output_path
        self.regex_template: str | Path = regex_template
        self.lang: str = lang
        self.zoom: float = zoom

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
                lang: str = self.lang
                if lang == "":
                    pdf_lang = translate_iso_to_tesseract(doc.GetLang())
                    lang = "eng" if pdf_lang is None else pdf_lang
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

                                xobj, temp_page_box = self._create_text_xobject_from_ocr(
                                    pdfix, doc, temp_pdf_page
                                )
                                self._add_xobject_to_page(pdfix, page, xobj, temp_page_box)
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

    def _add_xobject_to_page(
        self, pdfix: Pdfix, page: PdfPage, xobj: PdsStream, temp_page_box: PdfRect
    ) -> None:
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
