import tempfile

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
    kPdsPageText,
)
from tqdm import tqdm

import utils


class PdfixException(Exception):
    def __init__(self, message: str = ""):
        self.errno = GetPdfix().GetErrorType()
        self.add_note(message if len(message) else str(GetPdfix().GetError()))


# Renders a PDF page into a temporary file, which then used for OCR
def render_pages(page: PdfPage, pdfix: Pdfix, lang: str) -> bytes:
    """
    Render a PDF page into a temporary file, which is then used for OCR.

    Parameters
    ----------
    page : PdfPage
        The PDF page to be processed for OCR.
    pdfix : Pdfix
        The Pdfix SDK object.
    lang : str
        The language identifier for OCR.

    Returns
    -------
    bytes
        Raw PDF bytes.
    """
    zoom = 2.0
    pageView = page.AcquirePageView(zoom, kRotate0)
    if pageView is None:
        raise PdfixException("Unable to acquire page view")

    width = pageView.GetDeviceWidth()
    height = pageView.GetDeviceHeight()
    # Create an image
    image = pdfix.CreateImage(width, height, kImageDIBFormatArgb)
    if image is None:
        raise PdfixException("Unable to create image")

    # Render page
    renderParams = PdfPageRenderParams()
    renderParams.image = image
    renderParams.matrix = pageView.GetDeviceMatrix()
    if not page.DrawContent(renderParams):
        raise PdfixException("Unable to draw content")

    # Create temp file for rendering
    with tempfile.NamedTemporaryFile() as tmp:
        # Save image to file
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
    input_path: str,
    output_path: str,
    license_name: str,
    license_key: str,
    lang: str = "eng",
) -> None:
    """
    Run OCR using Tesseract.

    Parameters
    ----------
    input_path : str
        Input path to the PDF file.
    output_path : str
        Output path for saving the PDF file.
    license_name : str
        Pdfix SDK license name.
    license_key : str
        Pdfix SDK license key.
    lang : str, optional
        Language identifier for OCR Tesseract. Default value: "eng".
    """
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

    # Open doc
    doc = pdfix.OpenDoc(input_path, "")
    if doc is None:
        raise Exception("Unable to open pdf : " + pdfix.GetError())

    doc_num_pages = doc.GetNumPages()

    # Process each page
    for i in tqdm(range(0, doc_num_pages), desc="Processing pages"):
        page = doc.AcquirePage(i)
        if page is None:
            raise PdfixException("Unable to acquire page")

        try:
            temp_pdf = render_pages(page, pdfix, lang)
        except Exception as e:
            raise e
        with open("/data_out/example/temp.pdf", "w+b") as f:
            f.write(temp_pdf)

        temp_doc = pdfix.OpenDoc("/data_out/example/temp.pdf", "")

        if temp_doc is None:
            raise Exception("Unable to open pdf : " + str(pdfix.GetError()))

        # There is always only one page in the new PDF file
        temp_page = temp_doc.AcquirePage(0)
        temp_page_box = temp_page.GetCropBox()

        # Remove other then text page objects from the page content
        temp_page_content = temp_page.GetContent()
        for i in reversed(range(0, temp_page_content.GetNumObjects())):
            obj = temp_page_content.GetObject(i)
            obj_type = obj.GetObjectType()
            if not obj_type == kPdsPageText:
                temp_page_content.RemoveObject(obj)

        temp_page.SetContent()

        xobj = doc.CreateXObjectFromPage(temp_page)
        if xobj is None:
            raise Exception(
                "Failed to create XObject from page: " + str(pdfix.GetError())
            )

        temp_page.Release()
        temp_doc.Close()

        crop_box = page.GetCropBox()
        scale_x = (crop_box.right - crop_box.left) / (
            temp_page_box.right - temp_page_box.left
        )
        scale_y = (crop_box.top - crop_box.bottom) / (
            temp_page_box.top - temp_page_box.bottom
        )

        # Calculate matrix for placing xObject on a page
        rotate = (page.GetRotate() / 90) % 4
        matrix = PdfMatrix()
        matrix = utils.PdfMatrixRotate(matrix, rotate * utils.kPi / 2, False)
        matrix = utils.PdfMatrixScale(matrix, scale_x, scale_y, False)
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

    if not doc.Save(output_path, kSaveFull):
        raise Exception("Unable to save pdf : " + pdfix.GetError())
