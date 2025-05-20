from pdfixsdk import GetPdfix


class PdfixException(Exception):
    def __init__(self, message: str = "") -> None:
        self.errno = GetPdfix().GetErrorType()
        self.add_note(message if len(message) else str(GetPdfix().GetError()))
