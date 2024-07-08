import copy
import tempfile

from tqdm import tqdm

import pytesseract
from pdfixsdk.Pdfix import (
    GetPdfix,
    Pdfix,
    kSaveFull,
    kRotate0,
    kImageFormatJpg,
    kImageDIBFormatArgb,
    PdfPageRenderParams,
    PdfMatrix,
    kPsTruncate,
    PdfImageParams,
    PdfPage,
)

import utils


class PdfixException(Exception):
    def __init__(self, message: str = ""):
        self.errno = GetPdfix().GetErrorType()
        self.add_note(message if len(message) else str(GetPdfix().GetError()))


def render_pages(page: PdfPage, pdfix: Pdfix):
    """
    Renders a PDF page into a temporary file, which then used for OCR

    Params
    ------
    page: PdfPage
        Page for OCR

    pdfix : Pdfix
        Pdfix SDK object

    """
    zoom = 2.0
    pageView = page.AcquirePageView(zoom, kRotate0)
    if pageView is None:
        raise PdfixException("Unable to acquire page view")

    width = pageView.GetDeviceWidth()
    height = pageView.GetDeviceHeight()
    # create an image
    image = pdfix.CreateImage(width, height, kImageDIBFormatArgb)
    if image is None:
        raise PdfixException("Unable to create image")

    # render page
    renderParams = PdfPageRenderParams()
    renderParams.image = image
    renderParams.matrix = pageView.GetDeviceMatrix()
    if not page.DrawContent(renderParams):
        raise PdfixException("Unable to draw content")

    crop_box = page.GetCropBox()

    # calculate matrix for placing text on a page
    rotate = (page.GetRotate() / 90) % 4
    matrix = PdfMatrix()
    matrix = utils.PdfMatrixRotate(matrix, rotate * utils.kPi / 2, False)
    matrix = utils.PdfMatrixScale(matrix, 1 / zoom, 1 / zoom, False)
    if rotate == 0:
        matrix = utils.PdfMatrixTranslate(matrix, crop_box.left, crop_box.bottom, False)
    elif rotate == 1:
        matrix = utils.PdfMatrixTranslate(
            matrix, crop_box.right, crop_box.bottom, False
        )
    elif rotate == 2:
        matrix = utils.PdfMatrixTranslate(matrix, crop_box.right, crop_box.top, False)
    elif rotate == 3:
        matrix = utils.PdfMatrixTranslate(matrix, crop_box.left, crop_box.top, False)

    # create temp file for rendering
    with tempfile.NamedTemporaryFile() as tmp:
        # save image to file
        stm = pdfix.CreateFileStream(tmp.name + ".jpg", kPsTruncate)
        if stm is None:
            raise PdfixException("Unable to create file stream")

        imgParams = PdfImageParams()
        imgParams.format = kImageFormatJpg
        imgParams.quality = 100
        if not image.SaveToStream(stm, imgParams):
            raise PdfixException("Unable to save image to stream")

        pdf = pytesseract.image_to_pdf_or_hocr(tmp.name + ".jpg", extension="pdf")
        return pdf


def ocr(input_path: str, output_path: str):
    # List of available languages
    print("Available config files: {}".format(pytesseract.get_languages(config="")))

    pdfix = GetPdfix()
    if pdfix is None:
        raise Exception("Pdfix Initialization fail")

    if not pdfix.GetAccountAuthorization().Authorize("TEST", "5kCYsTvbZLNHy3wt"):
        raise Exception("Pdfix Authorization fail")

    # open doc
    doc = pdfix.OpenDoc(input_path, "")
    if doc is None:
        raise Exception("Unable to open pdf : " + pdfix.GetError())

    doc_num_pages = doc.GetNumPages()

    out_pdf_doc = pdfix.CreateDoc()
    if out_pdf_doc is None:
        raise Exception("Failed to create new pdf: " + str(pdfix.GetError()))

    for i in tqdm(range(0, doc_num_pages), desc="Processing pages"):
        page = doc.AcquirePage(i)
        if page is None:
            raise PdfixException("Unable to acquire page")

        new_pdf = render_pages(page, pdfix)
        with open("temp.pdf", "w+b") as f:
            f.write(new_pdf)
        page.Release()

        new_doc = pdfix.OpenDoc("temp.pdf", "")

        if new_doc is None:
            raise Exception("Unable to open pdf : " + str(pdfix.GetError()))

        # new_page = new_doc.AcquirePage(
        #     0
        # )  # this is ok because there is always only one page in the new PDF file

        if not out_pdf_doc.InsertPages(-1 + i, new_doc, 0, 0, 2):
            raise Exception("Failed to insert page: " + str(pdfix.GetError()))

        # new_page.Release()

    if not out_pdf_doc.Save(output_path, kSaveFull):
        raise Exception("Unable to save pdf : " + pdfix.GetError())

    # with open(output_path, "w+b") as f:
    #     f.write(new_pdf)  # pdf type is bytes by default
