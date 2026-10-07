from deep_translator import GoogleTranslator

from .languages import LANGUAGES


def translate_text(text, language, *, is_pdf=False):
    """Traduire en français avec les paramètres historiques de GoogleTranslator."""
    translator = GoogleTranslator(source=LANGUAGES[language]['translation'], target='fr')
    # Le PDF français était le seul parcours sans argument timeout.
    if is_pdf and language == 'Français':
        return translator.translate(text)
    return translator.translate(text, timeout=10)
