import pytesseract

from .languages import LANGUAGES


def extract_text(image, language, *, is_pdf=False):
    """Conserver les options Tesseract propres aux PDF et aux images françaises."""
    options = {}
    if is_pdf or language == 'Français':
        options['config'] = '--oem 3 --psm 6'
    return pytesseract.image_to_string(image, lang=LANGUAGES[language]['ocr'], **options)
