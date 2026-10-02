from contextlib import chdir
from html.parser import HTMLParser
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import parse_qs, urljoin, urlsplit

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse


class LoginFormParser(HTMLParser):
    """Lire l'action et les champs réellement envoyés par le formulaire affiché."""

    def __init__(self):
        super().__init__()
        self.forms = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'form':
            self.current = {'attrs': attrs, 'inputs': {}}
            self.forms.append(self.current)
        elif tag == 'input' and self.current is not None and attrs.get('name'):
            self.current['inputs'][attrs['name']] = attrs.get('value', '')

    def handle_endtag(self, tag):
        if tag == 'form':
            self.current = None


class AuthenticationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username='reader', email='reader@example.test', password='test-password',
        )

    def test_valid_login_redirects_to_home(self):
        response = self.client.post(reverse('login_view'), {
            'username': 'reader', 'password': 'test-password',
        })
        self.assertRedirects(response, reverse('reindex'))
        self.assertEqual(self.client.session['_auth_user_id'], str(self.user.pk))

    def test_invalid_login_keeps_user_anonymous(self):
        response = self.client.post(reverse('login_view'), {
            'username': 'reader', 'password': 'wrong-password',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Non correspondance')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_missing_credentials_are_rejected(self):
        response = self.client.post(reverse('login_view'), {'username': 'reader'})
        self.assertTrue(response.context['luf'].errors)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_inactive_user_cannot_log_in(self):
        self.user.is_active = False
        self.user.save(update_fields=['is_active'])
        self.client.post(reverse('login_view'), {
            'username': 'reader', 'password': 'test-password',
        })
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_logout_clears_session(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('deco'))
        self.assertRedirects(response, reverse('login_view'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_registration_creates_free_user_and_hashes_password(self):
        response = self.client.post(reverse('register'), {
            'profileType': 'utilisateur', 'ut-username': 'new-reader',
            'ut-email': 'new@example.test', 'ut-password': 'new-password',
            'ut-password2': 'new-password',
        })
        self.assertRedirects(response, reverse('login_view'))
        user = get_user_model().objects.get(username='new-reader')
        self.assertTrue(user.check_password('new-password'))
        self.assertFalse(user.state_abonnement)

    def test_anonymous_redirect_leads_to_usable_login_form(self):
        response = self.client.get(reverse('reindex'), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="password"')

    def test_native_login_without_next_redirects_to_home(self):
        response = self.client.post(reverse('login'), {
            'username': 'reader', 'password': 'test-password',
        })
        self.assertRedirects(response, reverse('reindex'))


    def post_displayed_login_form(self, page, page_url, password='test-password'):
        parser = LoginFormParser()
        parser.feed(page.content.decode())
        self.assertEqual(len(parser.forms), 1)
        form = parser.forms[0]
        self.assertEqual(form['attrs']['method'].lower(), 'post')
        self.assertIn('username', form['inputs'])
        self.assertIn('password', form['inputs'])
        self.assertIn('csrfmiddlewaretoken', form['inputs'])
        data = {**form['inputs'], 'username': 'reader', 'password': password}
        action = urljoin(page_url, form['attrs'].get('action', ''))
        return self.client.post(action, data), action

    def test_native_login_form_returns_to_requested_page_after_invalid_then_valid_login(self):
        self.client = Client(enforce_csrf_checks=True)
        # La vue d'upload vérifie des dossiers relatifs même en GET.
        with TemporaryDirectory(prefix='tsukiyomi-login-test-') as temporary:
            with chdir(temporary), self.settings(MEDIA_ROOT=Path(temporary) / 'media_upload'):
                destination = reverse('name_televerse_url_free') + '?source=login&step=2'
                redirect = self.client.get(destination)
                self.assertEqual(redirect.status_code, 302)
                login_url = redirect.url
                self.assertEqual(urlsplit(login_url).path, reverse('login'))
                self.assertEqual(parse_qs(urlsplit(login_url).query)['next'], [destination])
                page = self.client.get(login_url)
                self.assertEqual(page.status_code, 200)

                invalid, action = self.post_displayed_login_form(page, login_url, password='wrong')
                self.assertEqual(invalid.status_code, 200)
                self.assertNotIn('_auth_user_id', self.client.session)
                self.assertEqual(urlsplit(action).path, reverse('login'))

                response, action = self.post_displayed_login_form(invalid, action)
                self.assertEqual(urlsplit(action).path, reverse('login'))
                self.assertRedirects(response, destination)
                self.assertEqual(self.client.session['_auth_user_id'], str(self.user.pk))

    def test_custom_login_form_still_posts_to_custom_view(self):
        self.client = Client(enforce_csrf_checks=True)
        url = reverse('login_view')
        page = self.client.get(url)
        response, action = self.post_displayed_login_form(page, url)
        self.assertEqual(action, url)
        self.assertRedirects(response, reverse('reindex'))

    def test_native_login_form_does_not_redirect_to_external_next(self):
        self.client = Client(enforce_csrf_checks=True)
        url = reverse('login')
        page = self.client.get(url, {'next': 'https://example.test/untrusted/'})
        response, action = self.post_displayed_login_form(page, url)
        self.assertEqual(action, url)
        self.assertRedirects(response, reverse('reindex'))
