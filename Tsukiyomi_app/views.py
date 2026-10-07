from django.shortcuts import render, redirect
from .forms import DocumentForm, SubscribeForm
from .models import DocFile
from .services.extraction import count_pdf_pages, cleanup_previous_files
from .services.errors import DocumentProcessingError, document_errors
from .services.processor import process_document
from functools import wraps
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
import os
from django.core.mail import send_mass_mail
from .usage_policy import get_usage_policy
from django.conf import settings
import shutil
import logging
from smtplib import SMTPException

logger = logging.getLogger(__name__)


def _handle_document_errors(view):
    """Arrêter le traitement dès qu'une dépendance échoue, sans masquer les bugs Python."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        try:
            with document_errors():
                return view(request, *args, **kwargs)
        except DocumentProcessingError as error:
            logger.warning("Échec du traitement documentaire (%s)", type(error.__cause__).__name__)
            return render(request, 'tsukiyomi_app/televerse_page.html', {
                'DocForm': DocumentForm(prefix='pi'),
                'msg_error_televerse': (
                    "Le traitement ou l'envoi du document a échoué. "
                    "Aucun envoi réussi n'a été confirmé. Contactez l'administrateur."
                ),
            }, status=502)
    return wrapper


#vue qui permet de supprimer tous les fichiers uploadés depuis le repertoire media_upload/media via interface admin
@user_passes_test(
    lambda user: user.is_authenticated and user.is_active and user.is_superuser,
    login_url='login',
)
@require_POST
def clear_media_data(request):
    folder_media_upload = 'media_upload/media'
    
        
    if os.path.exists(folder_media_upload):
        for element in os.listdir(folder_media_upload):
            if element.endswith('.pdf') or element.endswith('.png') or element.startswith('.jpg') or element.endswith('.PDF'):
                shutil.rmtree(folder_media_upload)
            else:
                redirect('reindex')
    else:
        redirect('televerse_url')
    return render(request, 'tsukiyomi_app/index.html')
    



#vue de la page d'accueil

@login_required
def reindex(request):

    sf = SubscribeForm()

   
    user_online = request.user.state_abonnement
    if user_online == False:
        print(f"Abonnement de l'utilisateur: [Gratuit]")
        
    else:
        print(f"Abonnement de l'utilisateur: [payant]")
    
    return render(request, "tsukiyomi_app/index.html", context={
        'sf' : sf,
        
    })
    

@login_required
@_handle_document_errors
def get_televerse(request):
    """Valider l'upload et ses quotas, puis convertir le résultat métier en réponse HTTP."""
    policy = get_usage_policy(request.user)
    form = DocumentForm(prefix="pi")
    cleanup_previous_files(request.user)

    if 'profileType' in request.POST:
        if request.POST['profileType'] != 'pdf_img':
            return render(request, 'tsukiyomi_app/televerse_page.html', {'DocForm': form})

        form = DocumentForm(request.POST, request.FILES, prefix="pi")
        if form.is_valid():
            file_type = form.cleaned_data['type_file']
            limit = policy.max_pdf if file_type == 'PDF' else policy.max_images
            count = DocFile.objects.filter(user=request.user, type_file=file_type).count()
            if count >= limit:
                message = (
                    f"[ Limite de téléversement des fichiers PDF atteinte. vous n'avez droit qu'à {policy.max_pdf} fichiers pdf téléversés ...] "
                    if file_type == 'PDF' else "[ Limite de téléversement des fichiers Image atteinte ]"
                )
                return render(request, 'tsukiyomi_app/televerse_page.html', {
                    'msg_error_televerse': message,
                })

            document = form.save(commit=False)
            document.user = request.user
            if file_type == 'PDF' and count_pdf_pages(form.cleaned_data['button_televerse']) > policy.max_pdf_pages:
                return render(request, 'tsukiyomi_app/televerse_page.html', {
                    'msg_error_televerse': f"[Vous ne pouvez téléverser que des fichiers PDF de {policy.max_pdf_pages} pages maximum ]",
                })

            # La sauvegarde précède toujours les dépendances externes : un échec consomme le quota.
            document.save()
            result = process_document(document)
            text = result.text
            if result.output_path is None:
                text = "aucun text détecté ..." if file_type == 'PDF' else "aucun texte détecté ..."
            return render(request, 'tsukiyomi_app/succes_uploadfile.html', {'text': text})

    return render(request, 'tsukiyomi_app/televerse_page.html', {
        'DocForm': form,
        'notif_stage_process': None,
    })


def subscribe_view(request):
    sf = SubscribeForm()
    if request.method == 'POST':
    
        sf = SubscribeForm(request.POST or None)
        if sf.is_valid():
            subscriber = sf.save()
            try:

                sujet = "Bienvenu sur notre newsletter (TSUKIYOMI)"
                message = "Bonjour, Nous vous remerçions pour votre inscription"

                messages = [
                    (sujet, message, settings.DEFAULT_FROM_EMAIL, [subscriber.email])
                ]
                send_mass_mail(messages, fail_silently=False)

                msg_success_newsletter = 'Processus de newsletter réussi ...'
                print("processus de newsletter réussi ...")
                return render(request, 'tsukiyomi_app/index.html', context={
                    'msg_success_newsletter' : msg_success_newsletter,
                    'sf' : SubscribeForm()
                })
            except (OSError, SMTPException) as error:
                logger.warning("Échec de l'e-mail newsletter (%s)", type(error).__name__)
                sf.add_error(None, "L'inscription est enregistrée, mais l'e-mail de bienvenue n'a pas pu être envoyé.")
                return render(request, 'tsukiyomi_app/index.html', {'sf': sf}, status=502)

    return render(request, 'tsukiyomi_app/index.html', context={
        'sf' : sf
    })



def check_table_users(request):
    return render(request, "tsukiyomi_app/table_offre.html")
