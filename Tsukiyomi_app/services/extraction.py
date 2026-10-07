import os
import shutil

from pdf2image import convert_from_path
from PIL import Image
from PyPDF2 import PdfReader


def count_pdf_pages(upload):
    return len(PdfReader(upload).pages)


def pdf_pages(path, username):
    """Rasteriser systématiquement le PDF avec les dossiers et DPI existants."""
    media_folder = f'media_upload/media/mediaby{username}'
    os.makedirs(media_folder, exist_ok=True)
    os.makedirs(f'Tsukiyomi_doc/repository-{username}', exist_ok=True)
    return convert_from_path(path, dpi=300, output_folder=media_folder)


def open_image(path):
    """Ouvrir l'image ; l'appelant la ferme avec un bloc with."""
    return Image.open(path)


def cleanup_previous_files(username):
    """Conserver le nettoyage historique ; l'isolation des fichiers est hors Phase 4."""
    folders = (
        (f'tsukiyomi_doc/repository-{username}', '.docx'),
        (f'tsukiyomi_doc/repositoryImg-{username}', '.docx'),
        (f'media_upload/media/mediaby{username}', '.ppm'),
    )
    for folder, suffix in folders:
        if os.path.exists(folder):
            for name in os.listdir(folder):
                if name.endswith(suffix):
                    shutil.rmtree(folder)
