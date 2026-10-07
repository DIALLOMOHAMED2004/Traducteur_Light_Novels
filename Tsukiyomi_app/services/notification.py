from django.conf import settings
from django.core.mail import EmailMessage


def send_document(path, recipient, language):
    """Envoyer le DOCX final ; laisser remonter tout échec de pièce jointe ou SMTP."""
    email = EmailMessage(
        subject=f"Votre fichier de langue source {language} traduit en Français",
        body="Veuillez trouver ci-joint votre fichier traduit par TSUKIYOMI",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
    )
    email.attach_file(path)
    email.send(fail_silently=False)
