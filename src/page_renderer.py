from typing import BinaryIO

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


def render_page(pdfix: Pdfix, page: PdfPage, zoom: float, temporary_file: BinaryIO) -> None:
    """
    Render a PDF page into a temporary file, which is then used for OCR.

    Args:
        pdfix (Pdfix): The Pdfix SDK object.
        page (PdfPage): The PDF page to be processed for OCR.
        zoom (float): Zoom level for rendering the page.
        temporary_file (BinaryIO): Temporary file for saving image.

    Returns:
        Raw PDF bytes (OCR page).
    """
    page_view = page.AcquirePageView(zoom, kRotate0)
    if page_view is None:
        raise PdfixException(pdfix, "Unable to acquire page view")

    try:
        width = page_view.GetDeviceWidth()
        height = page_view.GetDeviceHeight()

        # Create an image
        image = pdfix.CreateImage(width, height, kImageDIBFormatArgb)
        if image is None:
            raise PdfixException(pdfix, "Unable to create image")

        try:
            # Render page
            render_params = PdfPageRenderParams()
            render_params.image = image
            render_params.matrix = page_view.GetDeviceMatrix()

            if not page.DrawContent(render_params):
                raise PdfixException(pdfix, "Unable to draw content")

            # Save image to file
            file_stream = pdfix.CreateFileStream(temporary_file.name + ".jpg", kPsTruncate)
            if file_stream is None:
                raise PdfixException(pdfix, "Unable to create file stream")

            try:
                img_params = PdfImageParams()
                img_params.format = kImageFormatJpg
                img_params.quality = 100

                if not image.SaveToStream(file_stream, img_params):
                    raise PdfixException(pdfix, "Unable to save image to stream")
            except Exception:
                raise
            finally:
                file_stream.Destroy()
        except Exception:
            raise
        finally:
            image.Destroy()
    except Exception:
        raise
    finally:
        page_view.Release()
