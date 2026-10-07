from concurrent.futures import ThreadPoolExecutor
from contextlib import chdir
from pathlib import Path
from smtplib import SMTPException
from tempfile import TemporaryDirectory
from threading import Event
from unittest.mock import patch
from uuid import UUID

from django.contrib.auth import get_user_model
from django.db import connections
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from docx import Document
from pytesseract.pytesseract import TesseractError

from .models import DocFile, TranslationJob
from .services.errors import DocumentProcessingError
from .services.processor import process_document
from .services.workspace import workspace_for
from .tests import image_upload, pdf_upload


class JobTestSetup:
    def setUp(self):
        super().setUp()
        temporary = TemporaryDirectory(prefix='tsukiyomi-jobs-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        config = self.settings(MEDIA_ROOT=self.root)
        config.enable()
        self.addCleanup(config.disable)
        self.user = get_user_model().objects.create_user(username='reader', email='reader@example.test')
        self.mock('socket.socket.connect', side_effect=AssertionError('Réseau interdit'))
        self.mock('subprocess.Popen', side_effect=AssertionError('Processus externe interdit'))
        self.convert = self.mock('Tsukiyomi_app.services.extraction.convert_from_path',
                                 side_effect=self.rasterize)
        self.ocr = self.mock('Tsukiyomi_app.services.processor.extract_text', return_value='Source')
        self.translate = self.mock('Tsukiyomi_app.services.processor.translate_text',
                                   side_effect=lambda text, *args, **kwargs: text)
        self.send = self.mock('Tsukiyomi_app.services.notification.EmailMessage.send',
                              autospec=True, return_value=1)

    def mock(self, target, **kwargs):
        patcher = patch(target, **kwargs)
        result = patcher.start()
        self.addCleanup(patcher.stop)
        return result

    def rasterize(self, source, *, dpi, output_folder, first_page, last_page, paths_only):
        self.assertEqual(first_page, last_page)
        self.assertTrue(paths_only)
        pages = [Path(output_folder) / f'page_{first_page:04d}.ppm']
        for page in pages:
            page.write_bytes(Path(source).read_bytes())
        return pages

    def job(self, kind='PDF', language='Anglais'):
        document = DocFile.objects.create(
            user=self.user, type_file=kind, type_language=language,
            button_televerse=pdf_upload(2) if kind == 'PDF' else image_upload(),
        )
        return TranslationJob.objects.create(user=self.user, source=document, source_language=language)

    def snapshot(self, root):
        return {p.relative_to(root): p.read_bytes() for p in root.rglob('*') if p.is_file()}

    def assert_output(self, job, text):
        job.refresh_from_db()
        self.assertEqual(job.status, TranslationJob.Status.SUCCEEDED)
        self.assertEqual(Path(job.output_file.path), workspace_for(job).output_dir / 'translation.docx')
        paragraphs = [p.text for p in Document(job.output_file.path).paragraphs
                      if p.text != 'TRADUIT PAR ZENIA']
        self.assertEqual(paragraphs, [text] * (2 if job.source.type_file == 'PDF' else 1))


class TranslationJobTests(JobTestSetup, TestCase):
    def test_creation_has_unique_uuid_relations_languages_and_pending_status(self):
        first, second = self.job(language='Japonais'), self.job('Image')
        first.refresh_from_db()
        self.assertIsInstance(first.pk, UUID)
        self.assertNotEqual(first.pk, second.pk)
        self.assertEqual(first.user, self.user)
        self.assertEqual(first.source.user, self.user)
        self.assertEqual(first.source.type_file, 'PDF')
        self.assertEqual(first.source_language, 'Japonais')
        self.assertEqual(first.target_language, 'Français')
        self.assertEqual(first.status, TranslationJob.Status.PENDING)
        self.assertIsNotNone(first.created_at)
        self.assertIsNone(first.started_at)
        self.assertIsNone(first.finished_at)
        self.assertEqual(first.error, '')
        self.assertFalse(first.output_file)
        self.assertFalse(workspace_for(first).root.exists())

    def test_processing_is_persisted_before_dependencies_and_success_after_email(self):
        for kind in ['PDF', 'Image']:
            with self.subTest(kind=kind):
                job = self.job(kind)

                def check_processing(*args, **kwargs):
                    saved = TranslationJob.objects.get(pk=job.pk)
                    self.assertEqual(saved.status, TranslationJob.Status.PROCESSING)
                    self.assertIsNotNone(saved.started_at)
                    self.assertIsNone(saved.finished_at)
                    self.assertFalse(saved.output_file)
                    return 'Source'

                self.ocr.side_effect = check_processing
                self.send.side_effect = check_processing
                result = process_document(job)
                self.assert_output(job, 'Source')
                self.assertEqual(result.output_path, job.output_file.path)
                self.assertEqual(job.error, '')
                self.assertLessEqual(job.created_at, job.started_at)
                self.assertLessEqual(job.started_at, job.finished_at)
                workspace = workspace_for(job)
                source = next(workspace.source_dir.iterdir())
                self.assertEqual(source.read_bytes(), Path(job.source.button_televerse.path).read_bytes())
                self.assertTrue(workspace.working_dir.is_dir())

    def test_expected_failures_record_only_cause_type_and_never_declare_success(self):
        for stage, error in [
            ('prepare_source', OSError('private source path')),
            ('rasterize_pdf_page', OSError('private poppler path')),
            ('extract_text', TesseractError(1, 'private OCR content')),
            ('translate_text', ConnectionError('private provider response')),
            ('write_docx', OSError('private disk path')),
            ('merge_docx', OSError('private merge path')),
            ('send_document', SMTPException('private recipient')),
        ]:
            with self.subTest(stage=stage):
                job = self.job()
                with patch(f'Tsukiyomi_app.services.processor.{stage}', side_effect=error):
                    with self.assertRaises(DocumentProcessingError) as caught:
                        process_document(job)
                self.assertIs(caught.exception.__cause__, error)
                job.refresh_from_db()
                self.assertEqual(job.status, TranslationJob.Status.FAILED)
                self.assertEqual(job.error, type(error).__name__)
                self.assertIsNotNone(job.finished_at)
                self.assertFalse(job.output_file)
                self.assertTrue(Path(job.source.button_televerse.path).is_file())
                if stage == 'send_document':
                    self.assertTrue((workspace_for(job).output_dir / 'translation.docx').is_file())
                self.send.assert_not_called()

    def test_unexpected_error_is_recorded_and_reraised_unchanged(self):
        job = self.job('Image')
        error = ValueError('private programming details')
        self.translate.side_effect = error
        with self.assertRaises(ValueError) as caught:
            process_document(job)
        self.assertIs(caught.exception, error)
        job.refresh_from_db()
        self.assertEqual(job.status, TranslationJob.Status.FAILED)
        self.assertEqual(job.error, 'ValueError')
        self.assertIsNotNone(job.finished_at)
        self.assertFalse(job.output_file)
        self.send.assert_not_called()

    def test_empty_ocr_is_success_without_artifact_or_email_including_later_pdf_page(self):
        for kind in ['PDF', 'Image']:
            for empty in ['', None]:
                with self.subTest(kind=kind, empty=empty):
                    job = self.job(kind)
                    self.ocr.side_effect = ['Source', empty] if kind == 'PDF' else [empty]
                    result = process_document(job)
                    job.refresh_from_db()
                    self.assertEqual(job.status, TranslationJob.Status.SUCCEEDED)
                    self.assertEqual(job.error, '')
                    self.assertIsNotNone(job.finished_at)
                    self.assertFalse(job.output_file)
                    self.assertIsNone(result.output_path)
                    self.assertEqual(list(workspace_for(job).output_dir.iterdir()), [])
                    self.send.assert_not_called()

    def test_two_jobs_of_same_user_preserve_all_previous_files(self):
        for first_kind, second_kind in [('PDF', 'PDF'), ('Image', 'Image'), ('PDF', 'Image')]:
            with self.subTest(kinds=(first_kind, second_kind)):
                first, second = self.job(first_kind), self.job(second_kind)
                self.ocr.return_value = 'JOB A'
                process_document(first)
                original = self.snapshot(workspace_for(first).root)
                self.ocr.return_value = 'JOB B'
                process_document(second)
                self.assertNotEqual(workspace_for(first), workspace_for(second))
                self.assertNotEqual(first.output_file.name, second.output_file.name)
                self.assertEqual(self.snapshot(workspace_for(first).root), original)
                self.assert_output(first, 'JOB A')
                self.assert_output(second, 'JOB B')

    def test_failed_job_does_not_modify_another_jobs_files(self):
        first, second = self.job(), self.job()
        process_document(first)
        original = self.snapshot(workspace_for(first).root)
        self.ocr.side_effect = ['Source', OSError('failure on second page')]
        with self.assertRaises(DocumentProcessingError):
            process_document(second)
        self.assertEqual(self.snapshot(workspace_for(first).root), original)
        self.assertFalse(second.output_file)
        self.assertEqual(list(workspace_for(second).output_dir.iterdir()), [])

    def test_same_job_cannot_be_started_twice_even_with_a_stale_instance(self):
        job = self.job()
        stale = TranslationJob.objects.get(pk=job.pk)
        process_document(job)
        original = self.snapshot(workspace_for(job).root)
        with self.assertRaises(ValueError):
            process_document(stale)
        self.assertEqual(self.snapshot(workspace_for(job).root), original)
        self.send.assert_called_once()
        self.assert_output(job, 'Source')

    def test_existing_workspace_is_never_overwritten(self):
        job = self.job()
        workspace = workspace_for(job)
        workspace.root.mkdir(parents=True)
        sentinel = workspace.root / 'sentinel'
        sentinel.write_bytes(b'preserve')
        with self.assertRaises(DocumentProcessingError):
            process_document(job)
        job.refresh_from_db()
        self.assertEqual(job.status, TranslationJob.Status.FAILED)
        self.assertEqual(job.error, 'FileExistsError')
        self.assertEqual(sentinel.read_bytes(), b'preserve')
        self.ocr.assert_not_called()

    def test_http_creates_pending_job_after_document_save_and_keeps_responses(self):
        self.client.force_login(self.user)

        def run(job):
            self.assertEqual(job.status, TranslationJob.Status.PENDING)
            self.assertEqual(job.source, DocFile.objects.get(pk=job.source_id))
            self.assertEqual(job.user, self.user)
            self.assertEqual(job.source_language, 'Japonais')
            return process_document(job)

        with patch('Tsukiyomi_app.views.process_document', side_effect=run):
            for fail in [False, True]:
                with self.subTest(fail=fail):
                    self.ocr.side_effect = OSError('private') if fail else None
                    response = self.client.post(reverse('televerse_url'), {
                        'profileType': 'pdf_img', 'pi-type_file': 'PDF',
                        'pi-type_language': 'Japonais', 'pi-button_televerse': pdf_upload(),
                    })
                    self.assertEqual(response.status_code, 502 if fail else 200)
                    job = TranslationJob.objects.latest('created_at')
                    self.assertEqual(job.status, 'FAILED' if fail else 'SUCCEEDED')
        self.assertEqual(DocFile.objects.count(), 2)
        self.assertEqual(TranslationJob.objects.count(), 2)

    def test_get_invalid_upload_page_limit_and_quota_create_no_job_or_cleanup(self):
        self.client.force_login(self.user)
        sentinel = self.root / 'media_upload/media/mediabyreader/old.ppm'
        sentinel.parent.mkdir(parents=True)
        sentinel.write_bytes(b'preserve')
        with chdir(self.root):
            self.assertEqual(self.client.get(reverse('televerse_url')).status_code, 200)
            for reason, upload in [('invalid', pdf_upload(name='invalid.txt')),
                                   ('pages', pdf_upload(6)), ('quota', pdf_upload())]:
                with self.subTest(reason=reason):
                    if reason == 'quota':
                        for _ in range(2):
                            DocFile.objects.create(user=self.user, type_file='PDF', type_language='Anglais',
                                                   button_televerse='media/old.pdf')
                    response = self.client.post(reverse('televerse_url'), {
                        'profileType': 'pdf_img', 'pi-type_file': 'PDF',
                        'pi-type_language': 'Anglais', 'pi-button_televerse': upload,
                    })
                    self.assertTemplateUsed(response, 'tsukiyomi_app/televerse_page.html')
        self.assertFalse(TranslationJob.objects.exists())
        self.assertFalse((self.root / 'jobs').exists())
        self.assertEqual(sentinel.read_bytes(), b'preserve')
        self.ocr.assert_not_called()


class ConcurrentJobTests(JobTestSetup, TransactionTestCase):
    def test_overlapping_jobs_share_no_files_for_pdf_pdf_image_image_and_pdf_image(self):
        for first_kind, second_kind in [('PDF', 'PDF'), ('Image', 'Image'), ('PDF', 'Image')]:
            with self.subTest(kinds=(first_kind, second_kind)):
                first, second = self.job(first_kind), self.job(second_kind)
                waiting, resume = Event(), Event()

                def ocr(image, language, **kwargs):
                    path = str(image if isinstance(image, Path) else image.filename)
                    if str(first.pk) in path:
                        waiting.set()
                        if not resume.wait(timeout=10):
                            raise AssertionError('Le second job ne termine pas')
                        return 'JOB A'
                    return 'JOB B'

                def run_first():
                    try:
                        return process_document(first)
                    finally:
                        connections.close_all()

                self.ocr.side_effect = ocr
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(run_first)
                    try:
                        self.assertTrue(waiting.wait(timeout=10))
                        self.assertEqual(TranslationJob.objects.get(pk=first.pk).status, 'PROCESSING')
                        with self.assertRaises(ValueError):
                            process_document(TranslationJob.objects.get(pk=first.pk))
                        original = self.snapshot(workspace_for(first).root)
                        process_document(second)
                        self.assertEqual(self.snapshot(workspace_for(first).root), original)
                        second_files = self.snapshot(workspace_for(second).root)
                    finally:
                        resume.set()
                    future.result(timeout=10)
                self.assertNotEqual(first.output_file.name, second.output_file.name)
                self.assertEqual(self.snapshot(workspace_for(second).root), second_files)
                self.assert_output(first, 'JOB A')
                self.assert_output(second, 'JOB B')
