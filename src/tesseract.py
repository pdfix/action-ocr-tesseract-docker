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
    PdsContent,
    kPdsPageText,
)

import utils


class PdfixException(Exception):
    def __init__(self, message: str = ""):
        self.errno = GetPdfix().GetErrorType()
        self.add_note(message if len(message) else str(GetPdfix().GetError()))


def render_pages(page: PdfPage, pdfix: Pdfix, lang: str):
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

        pdf = pytesseract.image_to_pdf_or_hocr(
            tmp.name + ".jpg", extension="pdf", lang=lang
        )
        return pdf


def ocr(
    input_path: str, output_path: str, license_name: str, license_key: str, lang: str
):
    # List of available languages
    print("Available config files: {}".format(pytesseract.get_languages(config="")))
    print("Using langauge: {}".format(lang))

    pdfix = GetPdfix()
    if pdfix is None:
        raise Exception("Pdfix Initialization fail")

    if license_name and license_key:
        if not pdfix.GetAccountAuthorization().Authorize(license_name, license_key):
            raise Exception("Pdfix Authorization fail")
    else:
        print("No license name or key provided. Using Pdfix trial")

    # open doc
    doc = pdfix.OpenDoc(input_path, "")
    if doc is None:
        raise Exception("Unable to open pdf : " + pdfix.GetError())

    doc_num_pages = doc.GetNumPages()

    for i in tqdm(range(0, doc_num_pages), desc="Processing pages"):
        page = doc.AcquirePage(i)
        if page is None:
            raise PdfixException("Unable to acquire page")

        tess_pdf = render_pages(page, pdfix, lang)
        with open("temp.pdf", "w+b") as f:
            f.write(tess_pdf)

        tess_doc = pdfix.OpenDoc("temp.pdf", "")

        if tess_doc is None:
            raise Exception("Unable to open pdf : " + str(pdfix.GetError()))

        tess_page = tess_doc.AcquirePage(
            0
        )  # this is ok because there is always only one page in the new PDF file

        # if not out_pdf_doc.InsertPages(-1 + i, new_doc, 0, 0, 2):
        #     raise Exception("Failed to insert page: " + str(pdfix.GetError()))

        tess_page_content = tess_page.GetContent()
        for i in reversed(range(0, tess_page_content.GetNumObjects())):
            obj = tess_page_content.GetObject(i)
            obj_type = obj.GetObjectType()
            if not obj_type == kPdsPageText:
                tess_page_content.RemoveObject(obj)

        tess_page.SetContent()

        xobj = doc.CreateXObjectFromPage(tess_page)
        if xobj is None:
            raise Exception(
                "Failed to create XObject from page: " + str(pdfix.GetError())
            )

        tess_page.Release()
        tess_doc.Close()

        crop_box = page.GetCropBox()
        zoom = 2

        # calculate matrix for placing text on a page
        rotate = (page.GetRotate() / 90) % 4
        matrix = PdfMatrix()
        matrix = utils.PdfMatrixRotate(matrix, rotate * utils.kPi / 2, False)
        matrix = utils.PdfMatrixScale(matrix, 1 / zoom, 1 / zoom, False)
        if rotate == 0:
            matrix = utils.PdfMatrixTranslate(
                matrix, crop_box.left, crop_box.bottom, False
            )
        elif rotate == 1:
            matrix = utils.PdfMatrixTranslate(
                matrix, crop_box.right, crop_box.bottom, False
            )
        elif rotate == 2:
            matrix = utils.PdfMatrixTranslate(
                matrix, crop_box.right, crop_box.top, False
            )
        elif rotate == 3:
            matrix = utils.PdfMatrixTranslate(
                matrix, crop_box.left, crop_box.top, False
            )

        content = page.GetContent()
        form = content.AddNewForm(-1, xobj, matrix)
        if form is None:
            raise Exception("Failed to add xobject to page: " + str(Pdfix.GetError()))

        # new_page.Release()

    if not doc.Save(output_path, kSaveFull):
        raise Exception("Unable to save pdf : " + pdfix.GetError())

    # with open(output_path, "w+b") as f:
    #     f.write(new_pdf)  # pdf type is bytes by default
