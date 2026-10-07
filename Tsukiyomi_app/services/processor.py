import os
from dataclasses import dataclass

from .errors import document_errors
from .extraction import pdf_pages, open_image
from .notification import send_document
from .ocr import extract_text
from .rendering import write_docx, merge_docx
from .translation import translate_text


@dataclass(frozen=True)
class ProcessingResult:
    """Dernière traduction et DOCX envoyé ; aucun artefact final si l'OCR est vide."""
    text: str | None
    output_path: str | None


@document_errors()
def process_document(document):
    """Traiter un DocFile validé et sauvegardé, sans HTTP ni modification de la base."""
    source = document.button_televerse.path
    language = document.type_language
    username = str(document.user)

    if document.type_file == 'PDF':
        pages = pdf_pages(source, username)
        folder = f'Tsukiyomi_doc/repository-{username}'
        page_paths = []
        for index, page in enumerate(pages):
            text = extract_text(page, language, is_pdf=True)
            if text == '' or text is None:
                return ProcessingResult(None, None)
            translated = translate_text(text, language, is_pdf=True)
            path = os.path.join(folder, f'trad_fr{index}.docx')
            write_docx(translated, path)
            page_paths.append(path)

        output_path = os.path.join(folder, f'trad_fusion_{username}.docx')
        merge_docx(page_paths, output_path)
        send_document(output_path, document.user.email, language)
    elif document.type_file == 'Image':
        with open_image(source) as image:
            folder = f'Tsukiyomi_doc/repositoryImg-{username}'
            os.makedirs(folder, exist_ok=True)
            text = extract_text(image, language)
            if text == '' or text is None:
                return ProcessingResult(None, None)
            translated = translate_text(text, language)
            output_path = os.path.join(folder, 'trad_fr.docx')
            write_docx(translated, output_path)
            send_document(output_path, document.user.email, language)
    else:
        raise ValueError(f'Type de document non pris en charge : {document.type_file}')

    return ProcessingResult(translated, output_path)
