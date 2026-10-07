from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from ..models import TranslationJob
from .errors import DocumentProcessingError, document_errors
from .extraction import pdf_page_texts, rasterize_pdf_page, open_image
from .notification import send_document
from .ocr import extract_text
from .rendering import write_docx, merge_docx
from .translation import translate_text
from .workspace import prepare_source, workspace_for


@dataclass(frozen=True)
class ProcessingResult:
    """Dernière traduction et DOCX envoyé ; aucun artefact final si l'OCR est vide."""
    text: str | None
    output_path: str | None


def process_document(job):
    """Exécuter une fois un job sauvegardé et tracer son résultat, sans HTTP."""
    job.started_at = timezone.now()
    # La transition conditionnelle empêche deux appels de traiter le même job.
    claimed = TranslationJob.objects.filter(pk=job.pk, status=TranslationJob.Status.PENDING).update(
        status=TranslationJob.Status.PROCESSING, started_at=job.started_at,
    )
    if not claimed:
        raise ValueError('Le job doit être sauvegardé et en attente.')
    job.status = TranslationJob.Status.PROCESSING
    try:
        with document_errors():
            if job.user_id != job.source.user_id or job.target_language != 'Français':
                raise ValueError('Utilisateur ou langue cible du job incompatible.')
            workspace = workspace_for(job)
            source = prepare_source(job, workspace)
            result = _process_document(job, source, workspace)
    except Exception as error:
        # Ne stocker ni texte source, ni message fournisseur, ni chemin sensible.
        cause = error.__cause__ if isinstance(error, DocumentProcessingError) else None
        job.error = type(cause or error).__name__
        job.status = TranslationJob.Status.FAILED
        job.finished_at = timezone.now()
        job.output_file = ''
        job.save(update_fields=['status', 'error', 'finished_at', 'output_file'])
        raise

    job.status = TranslationJob.Status.SUCCEEDED
    job.finished_at = timezone.now()
    job.error = ''
    job.output_file = (
        Path(result.output_path).relative_to(settings.MEDIA_ROOT).as_posix()
        if result.output_path else ''
    )
    job.save(update_fields=['status', 'finished_at', 'error', 'output_file'])
    return result


def _process_document(job, source, workspace):
    """Orchestrer les services existants dans les seuls dossiers du job."""
    document = job.source
    language = job.source_language
    output_path = str(workspace.output_dir / 'translation.docx')

    if document.type_file == 'PDF':
        page_paths = []
        for index, text in enumerate(pdf_page_texts(source)):
            if text is None:
                page = rasterize_pdf_page(source, workspace.working_dir, index + 1)
                text = extract_text(page, language, is_pdf=True)
            if text == '' or text is None:
                return ProcessingResult(None, None)
            translated = translate_text(text, language, is_pdf=True)
            path = str(workspace.working_dir / f'page_{index:04d}.docx')
            write_docx(translated, path)
            page_paths.append(path)

        merge_docx(page_paths, output_path)
        send_document(output_path, document.user.email, language)
    elif document.type_file == 'Image':
        with open_image(source) as image:
            text = extract_text(image, language)
            if text == '' or text is None:
                return ProcessingResult(None, None)
            translated = translate_text(text, language)
            write_docx(translated, output_path)
            send_document(output_path, document.user.email, language)
    else:
        raise ValueError(f'Type de document non pris en charge : {document.type_file}')

    return ProcessingResult(translated, output_path)
