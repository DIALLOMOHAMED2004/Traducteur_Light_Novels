from dataclasses import replace
from typing import Protocol

from deep_translator import GoogleTranslator

from .languages import LANGUAGES


class TranslationProvider(Protocol):
    """Appelable traduisant un texte en français ou propageant son erreur.

    `language` est l'une des six langues métier ; `is_pdf` permet de conserver
    les options historiques. Une simple fonction peut satisfaire ce contrat.
    """

    def __call__(self, text: str, language: str, *, is_pdf: bool = False) -> str:
        ...


def translate_text(text, language, *, is_pdf=False):
    """Traduire en français avec les paramètres historiques de GoogleTranslator."""
    translator = GoogleTranslator(source=LANGUAGES[language]['translation'], target='fr')
    # Le PDF français était le seul parcours sans argument timeout.
    if is_pdf and language == 'Français':
        return translator.translate(text)
    return translator.translate(text, timeout=10)


def translate_segments(segments, language, *, provider: TranslationProvider, is_pdf=False):
    """Traduire dans l'ordre sans modifier les sources ni envoyer les séparateurs."""
    return [
        replace(segment, translated_text=(
            segment.source_text if segment.kind == 'separator'
            else provider(segment.source_text, language, is_pdf=is_pdf)
        ))
        for segment in segments
    ]
