import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Segment:
    """Unité non persistée ; ordre dès 1 dans la page, identité dans le document."""

    id: str
    order: int
    page_number: int
    kind: str
    source_text: str
    translated_text: str | None = None


def _line_kind(line):
    if re.fullmatch(r'([*_=\-—※★☆])(?:[ \t]*\1){2,}', line):
        return 'separator'
    if re.fullmatch(r'#{1,6}[ \t]+\S.*', line):
        return 'heading'
    if re.match(r'[—–][ \t]+\S', line) or any(
        line.startswith(opening) and line.endswith(closing) and len(line) > 2
        for opening, closing in [('«', '»'), ('“', '”'), ('「', '」'), ('『', '』')]
    ):
        return 'dialogue'
    return 'paragraph'


def segment_text(text, page_number=1):
    """Découper une page en blocs ordonnés sans interpréter les mots.

    Les lignes vides délimitent les paragraphes ; un marqueur explicite isole
    une ligne (titre Markdown, dialogue ou séparateur). Les retours internes et
    marqueurs sont conservés, les fins de ligne normalisées en LF. Aucun titre
    n'est déduit de la longueur, de la langue ou des majuscules d'une ligne.
    """
    segments = []
    paragraph = []

    def append_segment(lines, kind):
        if lines:
            order = len(segments) + 1
            segments.append(Segment(
                id=f'p{page_number:04d}-s{order:04d}', order=order,
                page_number=page_number, kind=kind, source_text='\n'.join(lines),
            ))

    for line in text.splitlines():
        kind = _line_kind(line.strip())
        if not line.strip() or kind != 'paragraph':
            append_segment(paragraph, 'paragraph')
            paragraph = []
            if line.strip():
                append_segment([line], kind)
        else:
            paragraph.append(line)
    append_segment(paragraph, 'paragraph')
    return segments
