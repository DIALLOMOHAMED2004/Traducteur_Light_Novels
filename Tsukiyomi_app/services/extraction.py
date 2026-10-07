import re
import unicodedata

from pdf2image import convert_from_path
from PIL import Image
from PyPDF2 import PdfReader
from PyPDF2.errors import PdfReadError

from .errors import DocumentProcessingError


def count_pdf_pages(upload):
    return len(PdfReader(upload).pages)


def usable_native_text(text):
    """Filtrer les corruptions évidentes sans imposer de langue ni de longueur.

    Refuser les glyphes non décodés, contrôles anormaux et répétitions d'au
    moins huit lettres/chiffres identiques. Au moins la moitié des caractères
    visibles doivent être des lettres, nombres ou marques diacritiques Unicode.
    Ce filtre ne garantit ni le sens du texte ni son ordre de lecture.
    """
    if not text or re.search(r'\(cid:\d+\)|([^\W_])\1{7,}', text):
        return False
    if any(char == '\ufffd' or (
        unicodedata.category(char) in {'Cc', 'Cs', 'Co', 'Cn'} and char not in '\n\r\t'
    ) for char in text):
        return False
    visible = [char for char in text if not char.isspace()
               and unicodedata.category(char) != 'Cf']
    return any(char.isalnum() for char in visible) and sum(
        char.isalnum() or unicodedata.category(char).startswith('M') for char in visible
    ) >= len(visible) / 2


def pdf_page_texts(path):
    """Fournir le texte natif intact, ou None pour une page nécessitant l'OCR.

    Une erreur de décodage de page autorise l'OCR ; un PDF impossible à parcourir
    reste un échec documentaire. Les bugs Python ne sont pas interceptés.
    """
    try:
        reader = PdfReader(path)
        for page in reader.pages:
            try:
                text = page.extract_text()
            except PdfReadError:
                text = None
            yield text if usable_native_text(text) else None
    except PdfReadError as error:
        raise DocumentProcessingError(type(error).__name__) from error


def rasterize_pdf_page(path, working_dir, page_number):
    """Rasteriser la seule page demandée (numérotation dès 1), à 300 dpi."""
    return convert_from_path(
        path, dpi=300, output_folder=str(working_dir),
        first_page=page_number, last_page=page_number, paths_only=True,
    )[0]


def open_image(path):
    """Ouvrir l'image ; l'appelant la ferme avec un bloc with."""
    return Image.open(path)
