"""Configuration explicite des tests, sans connexion à la base PostgreSQL."""
import os

os.environ.setdefault('DJANGO_SECRET_KEY', 'tsukiyomi-tests-only-not-for-deployment')

from .settings import *  # noqa: F403,E402

DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
DEFAULT_FROM_EMAIL = 'tsukiyomi@example.test'
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
ALLOWED_HOSTS = ['testserver', 'localhost']
