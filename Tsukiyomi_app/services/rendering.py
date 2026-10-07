from docx import Document


def write_docx(segments, path):
    """Rendre les segments dans l'ordre fourni, avec le titre historique."""
    document = Document()
    document.add_heading('TRADUIT PAR ZENIA')
    for segment in segments:
        text = segment.translated_text
        if segment.kind == 'separator':
            text = segment.source_text
        elif text is None:
            raise ValueError('Segment sans traduction.')
        if segment.kind == 'heading':
            document.add_heading(text, level=1)
        else:
            style = 'Quote' if segment.kind == 'dialogue' else None
            document.add_paragraph(text, style=style)
    document.save(path)


def merge_docx(page_paths, output_path):
    """Fusionner uniquement les pages fournies, dans leur ordre explicite."""
    merged = Document()
    for path in page_paths:
        page = Document(path)
        for element in page.element.body:
            merged.element.body.append(element)
    merged.save(output_path)
