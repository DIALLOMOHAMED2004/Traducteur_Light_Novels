from contextlib import contextmanager
from smtplib import SMTPException

from deep_translator.exceptions import BaseError, RequestError, TooManyRequests
from pdf2image.exceptions import (
    PopplerNotInstalledError, PDFPageCountError, PDFSyntaxError, PDFPopplerTimeoutError,
)
from pytesseract.pytesseract import TesseractError
from requests.exceptions import RequestException


class DocumentProcessingError(Exception):
    """Échec attendu d'une dépendance, avec l'exception technique conservée comme cause."""


@contextmanager
def document_errors():
    """Traduire les erreurs prévues de Phase 2 sans masquer les bugs Python."""
    try:
        yield
    except (
        BaseError, RequestError, TooManyRequests, RequestException,
        TesseractError, PopplerNotInstalledError, PDFPageCountError,
        PDFSyntaxError, PDFPopplerTimeoutError, SMTPException, OSError,
    ) as error:
        raise DocumentProcessingError(type(error).__name__) from error
