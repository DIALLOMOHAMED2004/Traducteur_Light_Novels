from pdf2image import convert_from_path
from PIL import Image
from PyPDF2 import PdfReader


def count_pdf_pages(upload):
    return len(PdfReader(upload).pages)


def pdf_pages(path, working_dir):
    """Rasteriser à 300 dpi dans le dossier de travail du job."""
    return convert_from_path(path, dpi=300, output_folder=str(working_dir))


def open_image(path):
    """Ouvrir l'image ; l'appelant la ferme avec un bloc with."""
    return Image.open(path)
