FROM python:3.12-slim-bookworm@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        poppler-utils tesseract-ocr \
        tesseract-ocr-fra tesseract-ocr-eng tesseract-ocr-ita \
        tesseract-ocr-spa tesseract-ocr-jpn tesseract-ocr-chi-tra \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.lock ./
RUN python -m pip install --no-cache-dir -r requirements.lock \
    && python -m pip check

COPY . .
RUN useradd --uid 1000 --create-home tsukiyomi \
    && mkdir -p /app/media_upload \
    && chown tsukiyomi:tsukiyomi /app/media_upload

USER tsukiyomi
EXPOSE 8000

# Serveur local ; le déploiement de production reste une phase distincte.
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000", "--noreload"]
