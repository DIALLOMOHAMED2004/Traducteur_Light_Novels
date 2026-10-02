from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect, HttpResponseForbidden
from .forms import DocumentForm, SubscribeForm
from .models import DocFile, Subscriber
from pdf2image import convert_from_path
from PIL import Image
import pytesseract
from deep_translator import GoogleTranslator
from deep_translator.exceptions import BaseError, RequestError, TooManyRequests
from requests.exceptions import RequestException
from pdf2image.exceptions import (
    PopplerNotInstalledError, PDFPageCountError, PDFSyntaxError, PDFPopplerTimeoutError,
)
from pytesseract.pytesseract import TesseractError
from functools import wraps
from docx import Document
from docx2pdf import convert
from Tsukiyomi_account_app.models import UserTsukiyomi
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
import os
from PyPDF2 import PdfReader
from django.core.files import uploadedfile
from django.contrib import messages
from django.core.mail import send_mass_mail, EmailMessage
from .views_abonnement import check_abonnement_free, check_abonnement_paid
from django.conf import settings
import shutil
import logging
from smtplib import SMTPException

logger = logging.getLogger(__name__)


def _handle_document_errors(view):
    """Arrêter les deux vues dès qu'une dépendance échoue, sans masquer les bugs Python."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        try:
            return view(request, *args, **kwargs)
        except (
            BaseError, RequestError, TooManyRequests, RequestException,
            TesseractError, PopplerNotInstalledError, PDFPageCountError,
            PDFSyntaxError, PDFPopplerTimeoutError, SMTPException, OSError,
        ) as error:
            logger.warning("Échec du traitement documentaire (%s)", type(error).__name__)
            return render(request, 'tsukiyomi_app/televerse_page.html', {
                'DocForm': DocumentForm(prefix='pi'),
                'msg_error_televerse': (
                    "Le traitement ou l'envoi du document a échoué. "
                    "Aucun envoi réussi n'a été confirmé. Contactez l'administrateur."
                ),
            }, status=502)
    return wrapper
#import argostranslate.package, argostranslate.translate

#from datetime import datetime


#installation d'un package de traduction en_fr

#argostranslate.package.install_from_path("translate-en_fr.argosmodel")



config = '--oem 3 --psm 6'

state_admin_clear = False


#instances des documents de la base de données

ALL_DOC = DocFile.objects.all()

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
    

#vue qui ramene vers la page de televersement de fichier
@check_abonnement_free
@_handle_document_errors
def get_televerse(request):
    print(f"l'Utilisateur {request.user} a un abonnement gratuit ...")

    msg_error_televerse = None
    msg_error_extension_file = None
    msg_error_limite_page_pdf = None
    notif_stage_process = None
    DocForm = DocumentForm(prefix="pi")

    folder_root_tsukiyomi_doc = f'tsukiyomi_doc/repository-{request.user}'
    if os.path.exists(folder_root_tsukiyomi_doc):
        for element in os.listdir(folder_root_tsukiyomi_doc):
            if element.endswith('.docx'):
                shutil.rmtree(folder_root_tsukiyomi_doc)
            
    else:
        print('Repertoire PDF de sortie non existant ...')
        print('redirection vers la page de téléversement ...')
        redirect('televerse_url')


    folder_root_tsukiyomi_docImg = f'tsukiyomi_doc/repositoryImg-{request.user}'
    if os.path.exists(folder_root_tsukiyomi_docImg):
        for element in os.listdir(folder_root_tsukiyomi_docImg):
            if element.endswith('.docx'):
                shutil.rmtree(folder_root_tsukiyomi_docImg)
            
    else:
        print('Repertoire Img de sortie non existant ...')
        print('redirection vers la page de téléversement ...')
        redirect('televerse_url')

    
    folder_root_media = f'media_upload/media/mediaby{request.user}'

    if os.path.exists(folder_root_media):
        for elementmedia in os.listdir(folder_root_media):
            if elementmedia.endswith('.ppm'):
                shutil.rmtree(folder_root_media)
    else:
        print('Repertoire media non existant ...')
        print('redirection vers la page de téléversement ...')
        redirect('televerse_url')

    
    
    

    if len(request.POST) > 0 and 'profileType' in request.POST:
        DocForm = DocumentForm(prefix="pi")
        if request.POST['profileType'] == 'pdf_img':

            DocForm = DocumentForm(request.POST, request.FILES, prefix="pi")
            if DocForm.is_valid():
                notif_stage_process = f'[Processus en cours de traitement ...]'
                
                tf = DocForm.cleaned_data['type_file']
                ef = DocForm.cleaned_data['button_televerse']
                
                
                if (tf == 'PDF') and (str(ef).endswith('.pdf') or str(ef).endswith('.PDF')):  
                    print("Traitement fichier PDF ...")

                    #traitement des fichiers pdf   
                    #verification de la limite de televersement
                    existing_count_pdf_doc = ALL_DOC.filter(user=request.user, type_file="PDF").count()
                    
                     
                    
                    
                    

                    if (existing_count_pdf_doc <= 1):
                        DocFile = DocForm.save(commit=False)
                        if request.user.is_authenticated:
                            DocFile.user = request.user

                            reader = PdfReader(ef)
                            nbr_page = len(reader.pages)

                            if (nbr_page <= 5):
                                print(f"le nombre de page du document {ef} est de {nbr_page}")
                                print(f"{ef} est de type {type(ef)}")
                                print("ce qui correspond au quota requis ...")
                                print("le fichier peut donc être traité...")
                                DocFile.save()
                                

                                lang_select_pdf = DocForm.cleaned_data['type_language']
                                if lang_select_pdf == 'français' or lang_select_pdf == 'Français':
                                    a = DocFile.button_televerse.path

                                    os.makedirs(f'media_upload/media/mediaby{request.user}', exist_ok=True)
                                    os.makedirs(f'Tsukiyomi_doc/repository-{request.user}', exist_ok=True)

                                    pages = convert_from_path(a, dpi=300, output_folder= f'media_upload/media/mediaby{request.user}')

                                    #extraction du text de chaque page
                                    for i, page in enumerate(pages):
                                        text = pytesseract.image_to_string(page, lang='fra', config=config)
                                        if text == '' or text == None:
                                            text = "aucun text détecté ..."
                                            return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                                'text' : text
                                            })
                                        else:
                                            #traduction des pages convertis en image en francais
                                            #code pour traduire en francais le text extrait
                                            translated_fr = GoogleTranslator(source='fr', target='fr').translate(text)
                                            
                                            doc = Document()
                                            doc.add_heading('TRADUIT PAR ZENIA')
                                            doc.add_paragraph(translated_fr)

                                            print(f"un nouveau dossier pour l'utilisateur {request.user} sera crée ...")
                                            
                                            doc.save(f'Tsukiyomi_doc/repository-{request.user}/trad_fr{i}.docx')

                                    folder_doc = f'Tsukiyomi_doc/repository-{request.user}'
                                    merged_doc = Document()
                                    # Ne fusionner que les pages de ce PDF, dans leur ordre numérique.
                                    for page_index in range(len(pages)):
                                        docu = Document(os.path.join(folder_doc, f'trad_fr{page_index}.docx'))
                                        for element in docu.element.body:
                                            merged_doc.element.body.append(element)
                                    merged_doc.save(f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.docx')
                                    #convert(f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.docx', f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.pdf')
                                    mail_user = DocFile.user.email

                                            #transfert des fichiers traduits (.docx) sur la boite mail de l'utilisateur
                                            #le code ici
                                    print(f'soumission du fichier traité sur la boite mail {mail_user} ...')
                                    print("Envoie du fichier en piece jointe ...")
                                    pdf_traduit_final = f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.docx'

                                    email = EmailMessage(
                                        subject = f"Votre fichier de langue source {lang_select_pdf} traduit en Français",
                                        body = "Veuillez trouver ci-joint votre fichier traduit par TSUKIYOMI",
                                        from_email= settings.DEFAULT_FROM_EMAIL,
                                        to= [mail_user],
                                    
                                    )
                                    email.attach_file(pdf_traduit_final)
                                    email.send(fail_silently=False)
                                    print(f"Fichier transmis avec succès pour le compte {mail_user}")
                                    


                                           

                                            
                                        
                                    return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                                'text' : translated_fr
                                            })
                                
                                ################################################################################################
                                elif lang_select_pdf == 'anglais' or lang_select_pdf == 'Anglais':
                                    a = DocFile.button_televerse.path

                                    os.makedirs(f'media_upload/media/mediaby{request.user}', exist_ok=True)
                                    os.makedirs(f'Tsukiyomi_doc/repository-{request.user}', exist_ok=True)

                                    pages = convert_from_path(a, dpi=300, output_folder= f'media_upload/media/mediaby{request.user}')

                                    #extraction du text de chaque page
                                    for i, page in enumerate(pages):
                                        text = pytesseract.image_to_string(page, lang='eng', config=config)
                                        if text == '' or text == None:
                                            text = "aucun text détecté ..."
                                            return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                                'text' : text
                                            })
                                        else:
                                            #traduction des pages convertis en image en francais
                                            #code pour traduire en francais le text extrait
                                            translated_fr = GoogleTranslator(source='en', target='fr').translate(text, timeout=10)
                                            #translated_fr = argostranslate.translate.translate(text, "en", "fr")
                                            doc = Document()
                                            doc.add_heading('TRADUIT PAR ZENIA')
                                            doc.add_paragraph(translated_fr)

                                            print(f"un nouveau dossier pour l'utilisateur {request.user} sera crée ...")
                                            
                                            doc.save(f'Tsukiyomi_doc/repository-{request.user}/trad_fr{i}.docx')

                                    folder_doc = f'Tsukiyomi_doc/repository-{request.user}'
                                    merged_doc = Document()
                                    # Ne fusionner que les pages de ce PDF, dans leur ordre numérique.
                                    for page_index in range(len(pages)):
                                        docu = Document(os.path.join(folder_doc, f'trad_fr{page_index}.docx'))
                                        for element in docu.element.body:
                                            merged_doc.element.body.append(element)
                                    merged_doc.save(f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.docx')
                                    #convert(f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.docx', f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.pdf')
                                    mail_user = DocFile.user.email

                                            #transfert des fichiers traduits (.docx) sur la boite mail de l'utilisateur
                                            #le code ici
                                    print(f'soumission du fichier traité sur la boite mail {mail_user} ...')
                                    print("Envoie du fichier en piece jointe ...")
                                    pdf_traduit_final = f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.docx'

                                    email = EmailMessage(
                                        subject = f"Votre fichier de langue source {lang_select_pdf} traduit en Français",
                                        body = "Veuillez trouver ci-joint votre fichier traduit par TSUKIYOMI",
                                        from_email= settings.DEFAULT_FROM_EMAIL,
                                        to= [mail_user],
                                    
                                    )
                                    email.attach_file(pdf_traduit_final)
                                    email.send(fail_silently=False)
                                    print(f"Fichier transmis avec succès pour le compte {mail_user}")
                                    


                                           

                                            
                                        
                                    return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                                'text' : translated_fr
                                            })
                                #########################################################################################################
                                elif lang_select_pdf == 'italien' or lang_select_pdf == 'Italien':
                                    a = DocFile.button_televerse.path

                                    os.makedirs(f'media_upload/media/mediaby{request.user}', exist_ok=True)
                                    os.makedirs(f'Tsukiyomi_doc/repository-{request.user}', exist_ok=True)

                                    pages = convert_from_path(a, dpi=300, output_folder= f'media_upload/media/mediaby{request.user}')

                                    #extraction du text de chaque page
                                    for i, page in enumerate(pages):
                                        text = pytesseract.image_to_string(page, lang='ita', config=config)
                                        if text == '' or text == None:
                                            text = "aucun text détecté ..."
                                            return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                                'text' : text
                                            })
                                        else:
                                            #traduction des pages convertis en image en francais
                                            #code pour traduire en francais le text extrait
                                            translated_fr = GoogleTranslator(source='it', target='fr').translate(text, timeout=10)
                                            #translated_fr = argostranslate.translate.translate(text, "en", "fr")
                                            doc = Document()
                                            doc.add_heading('TRADUIT PAR ZENIA')
                                            doc.add_paragraph(translated_fr)

                                            print(f"un nouveau dossier pour l'utilisateur {request.user} sera crée ...")
                                            
                                            doc.save(f'Tsukiyomi_doc/repository-{request.user}/trad_fr{i}.docx')

                                    folder_doc = f'Tsukiyomi_doc/repository-{request.user}'
                                    merged_doc = Document()
                                    # Ne fusionner que les pages de ce PDF, dans leur ordre numérique.
                                    for page_index in range(len(pages)):
                                        docu = Document(os.path.join(folder_doc, f'trad_fr{page_index}.docx'))
                                        for element in docu.element.body:
                                            merged_doc.element.body.append(element)
                                    merged_doc.save(f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.docx')
                                    #convert(f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.docx', f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.pdf')
                                    mail_user = DocFile.user.email

                                            #transfert des fichiers traduits (.docx) sur la boite mail de l'utilisateur
                                            #le code ici
                                    print(f'soumission du fichier traité sur la boite mail {mail_user} ...')
                                    print("Envoie du fichier en piece jointe ...")
                                    pdf_traduit_final = f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.docx'

                                    email = EmailMessage(
                                        subject = f"Votre fichier de langue source {lang_select_pdf} traduit en Français",
                                        body = "Veuillez trouver ci-joint votre fichier traduit par TSUKIYOMI",
                                        from_email= settings.DEFAULT_FROM_EMAIL,
                                        to= [mail_user],
                                    
                                    )
                                    email.attach_file(pdf_traduit_final)
                                    email.send(fail_silently=False)
                                    print(f"Fichier transmis avec succès pour le compte {mail_user}")
                                    


                                           

                                            
                                        
                                    return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                                'text' : translated_fr
                                            })
                                ##########################################################################################################
                                elif lang_select_pdf == 'japonais' or lang_select_pdf == 'Japonais':
                                    a = DocFile.button_televerse.path

                                    os.makedirs(f'media_upload/media/mediaby{request.user}', exist_ok=True)
                                    os.makedirs(f'Tsukiyomi_doc/repository-{request.user}', exist_ok=True)

                                    pages = convert_from_path(a, dpi=300, output_folder= f'media_upload/media/mediaby{request.user}')

                                    #extraction du text de chaque page
                                    for i, page in enumerate(pages):
                                        text = pytesseract.image_to_string(page, lang='jpn', config=config)
                                        if text == '' or text == None:
                                            text = "aucun text détecté ..."
                                            return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                                'text' : text
                                            })
                                        else:
                                            #traduction des pages convertis en image en francais
                                            #code pour traduire en francais le text extrait
                                            translated_fr = GoogleTranslator(source='ja', target='fr').translate(text, timeout=10)
                                            #translated_fr = argostranslate.translate.translate(text, "en", "fr")
                                            doc = Document()
                                            doc.add_heading('TRADUIT PAR ZENIA')
                                            doc.add_paragraph(translated_fr)

                                            print(f"un nouveau dossier pour l'utilisateur {request.user} sera crée ...")
                                            
                                            doc.save(f'Tsukiyomi_doc/repository-{request.user}/trad_fr{i}.docx')

                                    folder_doc = f'Tsukiyomi_doc/repository-{request.user}'
                                    merged_doc = Document()
                                    # Ne fusionner que les pages de ce PDF, dans leur ordre numérique.
                                    for page_index in range(len(pages)):
                                        docu = Document(os.path.join(folder_doc, f'trad_fr{page_index}.docx'))
                                        for element in docu.element.body:
                                            merged_doc.element.body.append(element)
                                    merged_doc.save(f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.docx')
                                    #convert(f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.docx', f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.pdf')
                                    mail_user = DocFile.user.email

                                            #transfert des fichiers traduits (.docx) sur la boite mail de l'utilisateur
                                            #le code ici
                                    print(f'soumission du fichier traité sur la boite mail {mail_user} ...')
                                    print("Envoie du fichier en piece jointe ...")
                                    pdf_traduit_final = f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.docx'

                                    email = EmailMessage(
                                        subject = f"Votre fichier de langue source {lang_select_pdf} traduit en Français",
                                        body = "Veuillez trouver ci-joint votre fichier traduit par TSUKIYOMI",
                                        from_email= settings.DEFAULT_FROM_EMAIL,
                                        to= [mail_user],
                                    
                                    )
                                    email.attach_file(pdf_traduit_final)
                                    email.send(fail_silently=False)
                                    print(f"Fichier transmis avec succès pour le compte {mail_user}")
                                    


                                           

                                            
                                        
                                    return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                                'text' : translated_fr
                                            })
                                #############################################################################################################
                                elif lang_select_pdf == 'espagnol' or lang_select_pdf == 'Espagnol':
                                    a = DocFile.button_televerse.path

                                    os.makedirs(f'media_upload/media/mediaby{request.user}', exist_ok=True)
                                    os.makedirs(f'Tsukiyomi_doc/repository-{request.user}', exist_ok=True)

                                    pages = convert_from_path(a, dpi=300, output_folder= f'media_upload/media/mediaby{request.user}')

                                    #extraction du text de chaque page
                                    for i, page in enumerate(pages):
                                        text = pytesseract.image_to_string(page, lang='spa', config=config)
                                        if text == '' or text == None:
                                            text = "aucun text détecté ..."
                                            return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                                'text' : text
                                            })
                                        else:
                                            #traduction des pages convertis en image en francais
                                            #code pour traduire en francais le text extrait
                                            translated_fr = GoogleTranslator(source='es', target='fr').translate(text, timeout=10)
                                            #translated_fr = argostranslate.translate.translate(text, "en", "fr")
                                            doc = Document()
                                            doc.add_heading('TRADUIT PAR ZENIA')
                                            doc.add_paragraph(translated_fr)

                                            print(f"un nouveau dossier pour l'utilisateur {request.user} sera crée ...")
                                            
                                            doc.save(f'Tsukiyomi_doc/repository-{request.user}/trad_fr{i}.docx')

                                    folder_doc = f'Tsukiyomi_doc/repository-{request.user}'
                                    merged_doc = Document()
                                    # Ne fusionner que les pages de ce PDF, dans leur ordre numérique.
                                    for page_index in range(len(pages)):
                                        docu = Document(os.path.join(folder_doc, f'trad_fr{page_index}.docx'))
                                        for element in docu.element.body:
                                            merged_doc.element.body.append(element)
                                    merged_doc.save(f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.docx')
                                    #convert(f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.docx', f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.pdf')
                                    mail_user = DocFile.user.email

                                            #transfert des fichiers traduits (.docx) sur la boite mail de l'utilisateur
                                            #le code ici
                                    print(f'soumission du fichier traité sur la boite mail {mail_user} ...')
                                    print("Envoie du fichier en piece jointe ...")
                                    pdf_traduit_final = f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.docx'

                                    email = EmailMessage(
                                        subject = f"Votre fichier de langue source {lang_select_pdf} traduit en Français",
                                        body = "Veuillez trouver ci-joint votre fichier traduit par TSUKIYOMI",
                                        from_email= settings.DEFAULT_FROM_EMAIL,
                                        to= [mail_user],
                                    
                                    )
                                    email.attach_file(pdf_traduit_final)
                                    email.send(fail_silently=False)
                                    print(f"Fichier transmis avec succès pour le compte {mail_user}")
                                    


                                           

                                            
                                        
                                    return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                                'text' : translated_fr
                                            })
                                ############################################################################################################
                                elif lang_select_pdf == 'chinois' or lang_select_pdf == 'Chinois':
                                    a = DocFile.button_televerse.path

                                    os.makedirs(f'media_upload/media/mediaby{request.user}', exist_ok=True)
                                    os.makedirs(f'Tsukiyomi_doc/repository-{request.user}', exist_ok=True)

                                    pages = convert_from_path(a, dpi=300, output_folder= f'media_upload/media/mediaby{request.user}')

                                    #extraction du text de chaque page
                                    for i, page in enumerate(pages):
                                        text = pytesseract.image_to_string(page, lang='chi_tra', config=config)
                                        if text == '' or text == None:
                                            text = "aucun text détecté ..."
                                            return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                                'text' : text
                                            })
                                        else:
                                            #traduction des pages convertis en image en francais
                                            #code pour traduire en francais le text extrait
                                            translated_fr = GoogleTranslator(source='zh-TW', target='fr').translate(text, timeout=10)
                                            #translated_fr = argostranslate.translate.translate(text, "en", "fr")
                                            doc = Document()
                                            doc.add_heading('TRADUIT PAR ZENIA')
                                            doc.add_paragraph(translated_fr)

                                            print(f"un nouveau dossier pour l'utilisateur {request.user} sera crée ...")
                                            
                                            doc.save(f'Tsukiyomi_doc/repository-{request.user}/trad_fr{i}.docx')

                                    folder_doc = f'Tsukiyomi_doc/repository-{request.user}'
                                    merged_doc = Document()
                                    # Ne fusionner que les pages de ce PDF, dans leur ordre numérique.
                                    for page_index in range(len(pages)):
                                        docu = Document(os.path.join(folder_doc, f'trad_fr{page_index}.docx'))
                                        for element in docu.element.body:
                                            merged_doc.element.body.append(element)
                                    merged_doc.save(f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.docx')
                                    #convert(f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.docx', f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.pdf')
                                    mail_user = DocFile.user.email

                                            #transfert des fichiers traduits (.docx) sur la boite mail de l'utilisateur
                                            #le code ici
                                    print(f'soumission du fichier traité sur la boite mail {mail_user} ...')
                                    print("Envoie du fichier en piece jointe ...")
                                    pdf_traduit_final = f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.docx'

                                    email = EmailMessage(
                                        subject = f"Votre fichier de langue source {lang_select_pdf} traduit en Français",
                                        body = "Veuillez trouver ci-joint votre fichier traduit par TSUKIYOMI",
                                        from_email= settings.DEFAULT_FROM_EMAIL,
                                        to= [mail_user],
                                    
                                    )
                                    email.attach_file(pdf_traduit_final)
                                    email.send(fail_silently=False)
                                    print(f"Fichier transmis avec succès pour le compte {mail_user}")
                                    


                                           

                                            
                                        
                                    return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                                'text' : translated_fr
                                            })





                            else:
                                print("le quota a depassé la limite de page pour le traitement...")
                                print("vous ne pourrez pas téléverser votre fichier...")
                                msg_error_limite_page_pdf = "[En mode gratuit vous ne pouvez téléverser que des fichiers PDF de moins de 05 pages ]"
                                return render(request, 'tsukiyomi_app/televerse_page.html', context={
                                'msg_error_televerse' : msg_error_limite_page_pdf
                        }
                        )

                           
                            
                    else:
                        msg_error_televerse = "[ Limite de téléversement des fichiers PDF atteinte. vous n'avez droit qu'à 2 fichiers pdf téléversés ...] "     
                        return render(request, 'tsukiyomi_app/televerse_page.html', context={
                                'msg_error_televerse' : msg_error_televerse
                        }
                        )
                                        
                
                    
                elif (tf == 'Image') and (str(ef).endswith('.jpg') or str(ef).endswith('.png')):
                     print("Traitement fichier Image ...")
                     
                     #traitement des fichiers image
                     #verification de la limite de téléversement

                     
                     existing_count_img = ALL_DOC.filter(user=request.user, type_file="Image").count()
                   
                        
                     if (existing_count_img <= 2 ):
                        DocFile = DocForm.save(commit=False)
                        if request.user.is_authenticated:
                            DocFile.user = request.user
                            print(f"etat de connexion : {request.user.is_authenticated}")
                            print(f"type d'utilisateur : {request.user}")
                            DocFile.save()

                            #le traitement et la conversion se font ici
                            with Image.open(DocFile.button_televerse.path) as img:
                                lang_select = DocForm.cleaned_data['type_language']

                                #bloc gestion langue francaise
                                if lang_select == 'français' or lang_select == 'Français':
                                    
                                    os.makedirs(f'Tsukiyomi_doc/repositoryImg-{request.user}', exist_ok=True)
                                    text = pytesseract.image_to_string(img, lang='fra', config=config)
                                    if text == '' or text == None:
                                        text = "aucun texte détecté ..."
                                        return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                        'text' : text
                                         })
                                    else:
                                        

                                        #code de traduction du texte
                                        translated_fr = GoogleTranslator(source='fr', target='fr').translate(text, timeout=10)
                                            #translated_fr = argostranslate.translate.translate(text, "en", "fr")
                                        doc = Document()
                                        doc.add_heading('TRADUIT PAR ZENIA')
                                        doc.add_paragraph(translated_fr)
                                        
                                        print("le dossier Tsukiyomi_doc n'existe pas")
                                        
                                        doc.save(f'Tsukiyomi_doc/repositoryImg-{request.user}/trad_fr.docx')
                                        #convert('Tsukiyomi_doc/trad_fr.docx', 'Tsukiyomi_doc/trad_fr.pdf')
                                        mail_user = DocFile.user.email
                                            
                                          
                                        #transfert des fichiers traduits (.docx, .pdf) sur la boite mail de l'utilisateur
                                        #le code ici
                                        print(f'soumission du fichier traité sur la boite mail {mail_user} ...')
                                        print("Envoie du fichier en piece jointe ...")
                                        img_traduit_final = f'Tsukiyomi_doc/repositoryImg-{request.user}/trad_fr.docx'

                                        email = EmailMessage(
                                            subject = f"Votre fichier de langue source {lang_select} traduit en Français",
                                            body = "Veuillez trouver ci-joint votre fichier traduit par TSUKIYOMI",
                                            from_email= settings.DEFAULT_FROM_EMAIL,
                                            to= [mail_user],
                                        
                                        )
                                        email.attach_file(img_traduit_final)
                                        email.send(fail_silently=False)
                                        print(f"Fichier transmis avec succès pour le compte {mail_user}")


                                        return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                        'text' : translated_fr


                                        })
                                    ############################################################################################
                                    
                                elif lang_select == 'anglais' or lang_select == 'Anglais':
                                    os.makedirs(f'Tsukiyomi_doc/repositoryImg-{request.user}', exist_ok=True)
                                    text = pytesseract.image_to_string(img, lang='eng')
                                    if text == '' or text == None:
                                        text = "aucun texte détecté ..."
                                        return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                        'text' : text
                                         })
                                    else:
                                        #code de traduction du texte
                                        translated_fr = GoogleTranslator(source='en', target='fr').translate(text, timeout=10)
                                            #translated_fr = argostranslate.translate.translate(text, "en", "fr")
                                        doc = Document()
                                        doc.add_heading('TRADUIT PAR ZENIA')
                                        doc.add_paragraph(translated_fr)
                                        
                                        print("le dossier Tsukiyomi_doc n'existe pas")
                                        
                                        doc.save(f'Tsukiyomi_doc/repositoryImg-{request.user}/trad_fr.docx')
                                        #convert('Tsukiyomi_doc/trad_fr.docx', 'Tsukiyomi_doc/trad_fr.pdf')
                                        mail_user = DocFile.user.email
                                            
                                            
                                        #transfert des fichiers traduits (.docx, .pdf) sur la boite mail de l'utilisateur
                                        #le code ici
                                        print(f'soumission du fichier traité sur la boite mail {mail_user}')

                                        print("Envoie du fichier en piece jointe ...")
                                        img_traduit_final = f'Tsukiyomi_doc/repositoryImg-{request.user}/trad_fr.docx'

                                        email = EmailMessage(
                                            subject = f"Votre fichier de langue source {lang_select} traduit en Français",
                                            body = "Veuillez trouver ci-joint votre fichier traduit par TSUKIYOMI",
                                            from_email= settings.DEFAULT_FROM_EMAIL,
                                            to= [mail_user],
                                        
                                        )
                                        email.attach_file(img_traduit_final)
                                        email.send(fail_silently=False)
                                        print(f"Fichier transmis avec succès pour le compte {mail_user}")


                                        #apres soumission des fichiers à l'utilisateur via sa boite mail
                                        #suppression des fichiers sur le serveur
                                        # folder_tsukiyomi_doc = 'Tsukiyomi_doc'
                                        # shutil.rmtree(folder_tsukiyomi_doc)
                                       
                                        

                                        
                                        #suppresion des fichiers images stockées sur le serveur

                                        # folder_image_televerse = 'media_upload/media'
                                        # for fit in os.listdir(folder_image_televerse):
                                        #     if fit.endswith('.png') or fit.endswith('jpg'):
                                        #         path_file = os.path.join(folder_image_televerse, fit)
                                        #         os.remove(path_file)
                                    
                                        return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                        'text' : translated_fr


                                        })
                                    
                                elif lang_select == 'japonais' or lang_select == 'Japonais':
                                    os.makedirs(f'Tsukiyomi_doc/repositoryImg-{request.user}', exist_ok=True)
                                    text = pytesseract.image_to_string(img, lang='jpn')
                                    if text == '' or text == None:
                                        text = "aucun texte détecté ..."
                                        return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                        'text' : text
                                         })
                                    else:
                                        #code de traduction du texte
                                        translated_fr = GoogleTranslator(source='ja', target='fr').translate(text, timeout=10)
                                            #translated_fr = argostranslate.translate.translate(text, "en", "fr")
                                        doc = Document()
                                        doc.add_heading('TRADUIT PAR ZENIA')
                                        doc.add_paragraph(translated_fr)
                                        
                                        print("le dossier Tsukiyomi_doc n'existe pas")
                                       
                                        doc.save(f'Tsukiyomi_doc/repositoryImg-{request.user}/trad_fr.docx')
                                        #convert('Tsukiyomi_doc/trad_fr.docx', 'Tsukiyomi_doc/trad_fr.pdf')
                                        mail_user = DocFile.user.email
                                            
                                            
                                        #transfert des fichiers traduits (.docx, .pdf) sur la boite mail de l'utilisateur
                                        #le code ici
                                        print(f'soumission du fichier traité sur la boite mail {mail_user}')
                                        print("Envoie du fichier en piece jointe ...")
                                        img_traduit_final = f'Tsukiyomi_doc/repositoryImg-{request.user}/trad_fr.docx'

                                        email = EmailMessage(
                                            subject = f"Votre fichier de langue source {lang_select} traduit en Français",
                                            body = "Veuillez trouver ci-joint votre fichier traduit par TSUKIYOMI",
                                            from_email= settings.DEFAULT_FROM_EMAIL,
                                            to= [mail_user],
                                        
                                        )
                                        email.attach_file(img_traduit_final)
                                        email.send(fail_silently=False)
                                        print(f"Fichier transmis avec succès pour le compte {mail_user}")


                                        #apres soumission des fichiers à l'utilisateur via sa boite mail
                                        #suppression des fichiers sur le serveur
                                        # folder_tsukiyomi_doc = 'Tsukiyomi_doc'
                                        # shutil.rmtree(folder_tsukiyomi_doc)

                                        
                                        #suppresion des fichiers images stockées sur le serveur

                                        # folder_image_televerse = 'media_upload/media'
                                        # for fit in os.listdir(folder_image_televerse):
                                        #     if fit.endswith('.png') or fit.endswith('jpg'):
                                        #         path_file = os.path.join(folder_image_televerse, fit)
                                        #         os.remove(path_file)
                                    
                                        return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                        'text' : translated_fr


                                        })
                                    

                                elif lang_select == 'espagnol' or lang_select == 'Espagnol':
                                    os.makedirs(f'Tsukiyomi_doc/repositoryImg-{request.user}', exist_ok=True)
                                    text = pytesseract.image_to_string(img, lang='spa')
                                    if text == '' or text == None:
                                        text = "aucun texte détecté ..."
                                        return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                        'text' : text
                                         })
                                    else:
                                        #code de traduction du texte
                                        translated_fr = GoogleTranslator(source='es', target='fr').translate(text, timeout=10)
                                            #translated_fr = argostranslate.translate.translate(text, "en", "fr")
                                        doc = Document()
                                        doc.add_heading('TRADUIT PAR ZENIA')
                                        doc.add_paragraph(translated_fr)
                                        
                                        print("le dossier Tsukiyomi_doc n'existe pas")
                                        
                                        doc.save(f'Tsukiyomi_doc/repositoryImg-{request.user}/trad_fr.docx')
                                        #convert('Tsukiyomi_doc/trad_fr.docx', 'Tsukiyomi_doc/trad_fr.pdf')
                                        mail_user = DocFile.user.email
                                            
                                            
                                        #transfert des fichiers traduits (.docx, .pdf) sur la boite mail de l'utilisateur
                                        #le code ici
                                        print(f'soumission du fichier traité sur la boite mail {mail_user}')
                                        print("Envoie du fichier en piece jointe ...")
                                        img_traduit_final = f'Tsukiyomi_doc/repositoryImg-{request.user}/trad_fr.docx'

                                        email = EmailMessage(
                                            subject = f"Votre fichier de langue source {lang_select} traduit en Français",
                                            body = "Veuillez trouver ci-joint votre fichier traduit par TSUKIYOMI",
                                            from_email= settings.DEFAULT_FROM_EMAIL,
                                            to= [mail_user],
                                        
                                        )
                                        email.attach_file(img_traduit_final)
                                        email.send(fail_silently=False)
                                        print(f"Fichier transmis avec succès pour le compte {mail_user}")


                                        #apres soumission des fichiers à l'utilisateur via sa boite mail
                                        #suppression des fichiers sur le serveur
                                        # folder_tsukiyomi_doc = 'Tsukiyomi_doc'
                                        # shutil.rmtree(folder_tsukiyomi_doc)
                                        

                                        
                                        # #suppresion des fichiers images stockées sur le serveur

                                        # folder_image_televerse = 'media_upload/media'
                                        # for fit in os.listdir(folder_image_televerse):
                                        #     if fit.endswith('.png') or fit.endswith('jpg'):
                                        #         path_file = os.path.join(folder_image_televerse, fit)
                                        #         os.remove(path_file)
                                    
                                        return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                        'text' : translated_fr


                                        })
                                
                                elif lang_select == 'chinois' or lang_select == 'Chinois':
                                    os.makedirs(f'Tsukiyomi_doc/repositoryImg-{request.user}', exist_ok=True)
                                    text = pytesseract.image_to_string(img, lang='chi_tra')
                                    if text == '' or text == None:
                                        text = "aucun texte détecté ..."
                                        return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                        'text' : text
                                         })
                                    else:
                                        #code de traduction du texte
                                        translated_fr = GoogleTranslator(source='zh-TW', target='fr').translate(text, timeout=10)
                                            #translated_fr = argostranslate.translate.translate(text, "en", "fr")
                                        doc = Document()
                                        doc.add_heading('TRADUIT PAR ZENIA')
                                        doc.add_paragraph(translated_fr)
                                        
                                        print("le dossier Tsukiyomi_doc n'existe pas")
                                        
                                        doc.save(f'Tsukiyomi_doc/repositoryImg-{request.user}/trad_fr.docx')
                                        #convert('Tsukiyomi_doc/trad_fr.docx', 'Tsukiyomi_doc/trad_fr.pdf')
                                        mail_user = DocFile.user.email
                                            
                                            
                                        #transfert des fichiers traduits (.docx, .pdf) sur la boite mail de l'utilisateur
                                        #le code ici
                                        print(f'soumission du fichier traité sur la boite mail {mail_user}')
                                        print("Envoie du fichier en piece jointe ...")
                                        img_traduit_final = f'Tsukiyomi_doc/repositoryImg-{request.user}/trad_fr.docx'

                                        email = EmailMessage(
                                            subject = f"Votre fichier de langue source {lang_select} traduit en Français",
                                            body = "Veuillez trouver ci-joint votre fichier traduit par TSUKIYOMI",
                                            from_email= settings.DEFAULT_FROM_EMAIL,
                                            to= [mail_user],
                                        
                                        )
                                        email.attach_file(img_traduit_final)
                                        email.send(fail_silently=False)
                                        print(f"Fichier transmis avec succès pour le compte {mail_user}")


                                        #apres soumission des fichiers à l'utilisateur via sa boite mail
                                        #suppression des fichiers sur le serveur
                                        # folder_tsukiyomi_doc = 'Tsukiyomi_doc'
                                        # shutil.rmtree(folder_tsukiyomi_doc)
                                        

                                        
                                        # #suppresion des fichiers images stockées sur le serveur

                                        # folder_image_televerse = 'media_upload/media'
                                        # for fit in os.listdir(folder_image_televerse):
                                        #     if fit.endswith('.png') or fit.endswith('jpg'):
                                        #         path_file = os.path.join(folder_image_televerse, fit)
                                        #         os.remove(path_file)
                                    
                                        return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                        'text' : translated_fr


                                        })
                                    
                                
                                elif lang_select == 'italien' or lang_select == 'Italien':
                                    os.makedirs(f'Tsukiyomi_doc/repositoryImg-{request.user}', exist_ok=True)
                                    text = pytesseract.image_to_string(img, lang='ita')
                                    if text == '' or text == None:
                                        text = "aucun texte détecté ..."
                                        return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                        'text' : text
                                         })
                                    else:
                                        #code de traduction du texte
                                        translated_fr = GoogleTranslator(source='it', target='fr').translate(text, timeout=10)
                                            #translated_fr = argostranslate.translate.translate(text, "en", "fr")
                                        doc = Document()
                                        doc.add_heading('TRADUIT PAR ZENIA')
                                        doc.add_paragraph(translated_fr)
                                        
                                        print("le dossier Tsukiyomi_doc n'existe pas")
                                        
                                        doc.save(f'Tsukiyomi_doc/repositoryImg-{request.user}/trad_fr.docx')
                                        #convert('Tsukiyomi_doc/trad_fr.docx', 'Tsukiyomi_doc/trad_fr.pdf')
                                        mail_user = DocFile.user.email
                                            
                                            
                                        #transfert des fichiers traduits (.docx, .pdf) sur la boite mail de l'utilisateur
                                        #le code ici
                                        print(f'soumission du fichier traité sur la boite mail {mail_user}')
                                        print("Envoie du fichier en piece jointe ...")
                                        img_traduit_final = f'Tsukiyomi_doc/repositoryImg-{request.user}/trad_fr.docx'

                                        email = EmailMessage(
                                            subject = f"Votre fichier de langue source {lang_select} traduit en Français",
                                            body = "Veuillez trouver ci-joint votre fichier traduit par TSUKIYOMI",
                                            from_email= settings.DEFAULT_FROM_EMAIL,
                                            to= [mail_user],
                                        
                                        )
                                        email.attach_file(img_traduit_final)
                                        email.send(fail_silently=False)
                                        print(f"Fichier transmis avec succès pour le compte {mail_user}")


                                        #apres soumission des fichiers à l'utilisateur via sa boite mail
                                        #suppression des fichiers sur le serveur
                                        # folder_tsukiyomi_doc = 'Tsukiyomi_doc'
                                        # shutil.rmtree(folder_tsukiyomi_doc)
                                        

                                        
                                        # #suppresion des fichiers images stockées sur le serveur

                                        # folder_image_televerse = 'media_upload/media'
                                        # for fit in os.listdir(folder_image_televerse):
                                        #     if fit.endswith('.png') or fit.endswith('jpg'):
                                        #         path_file = os.path.join(folder_image_televerse, fit)
                                        #         os.remove(path_file)
                                    
                                        return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                        'text' : translated_fr


                                        })
                                    
                                
                                
                                

                                else:
                                    text = "Cette langue n'est pas prise en compte pour le moment..."                                                          
                                    #print("aucun text detecté")
                                    return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                        'text' : text


                                        })
                                    



                           # return redirect('pdf_or_image')
                        else:
                            print(f"etat de connexion : {request.user.is_authenticated}")
                            print(f"type d'utilisateur : {request.user}")
                                
                            return HttpResponseForbidden("Vous devez vous connecter.")
                    
                    
                     else:
                        msg_error_televerse = "[ Limite de téléversement des fichiers Image atteinte ]"
                           
                        return render(request, 'tsukiyomi_app/televerse_page.html', context={
                                'msg_error_televerse' : msg_error_televerse
                            })



                else:
                    msg_error_extension_file = "le type et l'extension de votre fichier téléversé ne correspondent pas ..."
                
                    return render(request, 'tsukiyomi_app/televerse_page.html', context={
                        'msg_error_extension_file' : msg_error_extension_file
                    })
    
                
                
                
        
            
        else:
            DocForm = DocumentForm(prefix="pi")
            return render(request, 'tsukiyomi_app/televerse_page.html', context={
                'DocForm': DocForm
            })
        
    return render(request, 'tsukiyomi_app/televerse_page.html', context={
                'DocForm': DocForm,
                'notif_stage_process' : notif_stage_process
            })
    



    
    


#vue qui route le traitement du fichier en fonction de son type ('pdf' ou 'image')
# def return_pdf_or_image_parse(request):
#     print("un fichier de l'utilisateur a ete uploadé...")
    

    



   

    






    #logique de la recuperation du document (image, pdf) depuis la base de donnéés
    

    # etapes 1: 
        #verification du type de document (pdf ou image)
        #en fonction du type de document, verifier leur limite de televersement par utilisateur
        #si pdf --> limite <= 2, si image --> limite <= 3
        #l'utilisateur ne doit pas depasser la limite de televersment
        #apres avoir conditionné sur le type de document et la limite de televersement
        #retourner le traffic vers parse_doc_pdf si type = pdf, ou parse_image si type = image
        



   # return render(request, 'tsukiyomi_app/succes_uploadfile.html')
    


#vue qui traite les fichiers televersé de type pdf
#def parse_doc_pdf(request):
    #on verifie le quota de televersement de l'utilisateur connecté
    #si sa limite est comprise entre [0 .. 2] on peut traiter le document,
    #si le nombre de page du document ne depasse pas 10 pages

        #on recupère le document et on le converti pour pouvoir le traduire
        #le fichier de sortie converti et traduit sera sauvegardé en .docx et en .pdf 
        #dans le gestionnaire de fichier de l'utilsateur (dans un dossier specifique)
        #le fichier pourra s'afficher depuis une couveuse de pdf depuis notre plateforme


    #  si non renvoyer erreur de limite et revenir sur la page de televersement
    
    # print("bienvenue sur la vue de traitement des fichiers PDF")

    # DocForm = DocumentForm(request.POST, request.FILES, prefix="pi")

    # meta_file_pdf_extension = DocForm.cleaned_data["button_televerse"]
    # print(f"le fichier recuperé est bien : {meta_file_pdf_extension}")


    # return render(request, 'tsukiyomi_app/succes_uploadfile.html')


# #vue qui traite les fichiers televersé de type image
# def parse_image(request):
#     #meme processus que pour le traitement de pdf
#     #à la seule difference que la limite des images ici sera de 3
#     print("bienvenue sur la vue de traitement des fichiers Image")
#     DocForm = DocumentForm(request.POST, request.FILES, prefix="pi")

#     meta_file_pdf_extension = DocForm.cleaned_data["button_televerse"]
#     print(f"le fichier recuperé est bien : {meta_file_pdf_extension}")


#     return render(request, 'tsukiyomi_app/succes_uploadfile.html')





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




#---------------------------------VUES ACCES PAYANT--------------------------------------------------------

@check_abonnement_paid
@_handle_document_errors
def get_televerse2(request):
    print(f"l'Utilisateur {request.user} a un abonnement payant ...")

    msg_error_televerse = None
    msg_error_extension_file = None
    msg_error_limite_page_pdf = None
    notif_stage_process = None
    DocForm = DocumentForm(prefix="pi")

    folder_root_tsukiyomi_doc = f'tsukiyomi_doc/repository-{request.user}'
    if os.path.exists(folder_root_tsukiyomi_doc):
        for element in os.listdir(folder_root_tsukiyomi_doc):
            if element.endswith('.docx'):
                shutil.rmtree(folder_root_tsukiyomi_doc)
            
    else:
        print('Repertoire PDF de sortie non existant ...')
        print('redirection vers la page de téléversement ...')
        redirect('televerse_url')


    folder_root_tsukiyomi_docImg = f'tsukiyomi_doc/repositoryImg-{request.user}'
    if os.path.exists(folder_root_tsukiyomi_docImg):
        for element in os.listdir(folder_root_tsukiyomi_docImg):
            if element.endswith('.docx'):
                shutil.rmtree(folder_root_tsukiyomi_docImg)
            
    else:
        print('Repertoire Img de sortie non existant ...')
        print('redirection vers la page de téléversement ...')
        redirect('televerse_url')

    
    folder_root_media = f'media_upload/media/mediaby{request.user}'

    if os.path.exists(folder_root_media):
        for elementmedia in os.listdir(folder_root_media):
            if elementmedia.endswith('.ppm'):
                shutil.rmtree(folder_root_media)
    else:
        print('Repertoire media non existant ...')
        print('redirection vers la page de téléversement ...')
        redirect('televerse_url')

    
    
    

    if len(request.POST) > 0 and 'profileType' in request.POST:
        DocForm = DocumentForm(prefix="pi")
        if request.POST['profileType'] == 'pdf_img':

            DocForm = DocumentForm(request.POST, request.FILES, prefix="pi")
            if DocForm.is_valid():
                notif_stage_process = f'[Processus en cours de traitement ...]'
                
                tf = DocForm.cleaned_data['type_file']
                ef = DocForm.cleaned_data['button_televerse']
                
                
                if (tf == 'PDF') and (str(ef).endswith('.pdf') or str(ef).endswith('.PDF')):  
                    print("Traitement fichier PDF ...")

                    #traitement des fichiers pdf   
                    #verification de la limite de televersement
                    existing_count_pdf_doc = ALL_DOC.filter(user=request.user, type_file="PDF").count()
                    
                     
                    
                    
                    

                    if (existing_count_pdf_doc <= 9):
                        DocFile = DocForm.save(commit=False)
                        if request.user.is_authenticated:
                            DocFile.user = request.user

                            reader = PdfReader(ef)
                            nbr_page = len(reader.pages)

                            if (nbr_page <= 30):
                                print(f"le nombre de page du document {ef} est de {nbr_page}")
                                print(f"{ef} est de type {type(ef)}")
                                print("ce qui correspond au quota requis ...")
                                print("le fichier peut donc être traité...")
                                DocFile.save()
                                

                                lang_select_pdf = DocForm.cleaned_data['type_language']
                                if lang_select_pdf == 'français' or lang_select_pdf == 'Français':
                                    a = DocFile.button_televerse.path

                                    os.makedirs(f'media_upload/media/mediaby{request.user}', exist_ok=True)
                                    os.makedirs(f'Tsukiyomi_doc/repository-{request.user}', exist_ok=True)

                                    pages = convert_from_path(a, dpi=300, output_folder= f'media_upload/media/mediaby{request.user}')

                                    #extraction du text de chaque page
                                    for i, page in enumerate(pages):
                                        text = pytesseract.image_to_string(page, lang='fra', config=config)
                                        if text == '' or text == None:
                                            text = "aucun text détecté ..."
                                            return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                                'text' : text
                                            })
                                        else:
                                            #traduction des pages convertis en image en francais
                                            #code pour traduire en francais le text extrait
                                            translated_fr = GoogleTranslator(source='fr', target='fr').translate(text)
                                            
                                            doc = Document()
                                            doc.add_heading('TRADUIT PAR ZENIA')
                                            doc.add_paragraph(translated_fr)

                                            print(f"un nouveau dossier pour l'utilisateur {request.user} sera crée ...")
                                            
                                            doc.save(f'Tsukiyomi_doc/repository-{request.user}/trad_fr{i}.docx')

                                    folder_doc = f'Tsukiyomi_doc/repository-{request.user}'
                                    merged_doc = Document()
                                    # Ne fusionner que les pages de ce PDF, dans leur ordre numérique.
                                    for page_index in range(len(pages)):
                                        docu = Document(os.path.join(folder_doc, f'trad_fr{page_index}.docx'))
                                        for element in docu.element.body:
                                            merged_doc.element.body.append(element)
                                    merged_doc.save(f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.docx')
                                    #convert(f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.docx', f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.pdf')
                                    mail_user = DocFile.user.email

                                            #transfert des fichiers traduits (.docx) sur la boite mail de l'utilisateur
                                            #le code ici
                                    print(f'soumission du fichier traité sur la boite mail {mail_user}')
                                    print("Envoie du fichier en piece jointe ...")
                                    pdf_traduit_final = f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.docx'

                                    email = EmailMessage(
                                        subject = f"Votre fichier de langue source {lang_select_pdf} traduit en Français",
                                        body = "Veuillez trouver ci-joint votre fichier traduit par TSUKIYOMI",
                                        from_email= settings.DEFAULT_FROM_EMAIL,
                                        to= [mail_user],
                                    
                                    )
                                    email.attach_file(pdf_traduit_final)
                                    email.send(fail_silently=False)
                                    print(f"Fichier transmis avec succès pour le compte {mail_user}")



                                           

                                            
                                        
                                    return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                                'text' : translated_fr
                                            })
                                
                                ################################################################################################
                                elif lang_select_pdf == 'anglais' or lang_select_pdf == 'Anglais':
                                    a = DocFile.button_televerse.path

                                    os.makedirs(f'media_upload/media/mediaby{request.user}', exist_ok=True)
                                    os.makedirs(f'Tsukiyomi_doc/repository-{request.user}', exist_ok=True)

                                    pages = convert_from_path(a, dpi=300, output_folder= f'media_upload/media/mediaby{request.user}')

                                    #extraction du text de chaque page
                                    for i, page in enumerate(pages):
                                        text = pytesseract.image_to_string(page, lang='eng', config=config)
                                        if text == '' or text == None:
                                            text = "aucun text détecté ..."
                                            return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                                'text' : text
                                            })
                                        else:
                                            #traduction des pages convertis en image en francais
                                            #code pour traduire en francais le text extrait
                                            translated_fr = GoogleTranslator(source='en', target='fr').translate(text, timeout=10)
                                            #translated_fr = argostranslate.translate.translate(text, "en", "fr")
                                            doc = Document()
                                            doc.add_heading('TRADUIT PAR ZENIA')
                                            doc.add_paragraph(translated_fr)

                                            print(f"un nouveau dossier pour l'utilisateur {request.user} sera crée ...")
                                            
                                            doc.save(f'Tsukiyomi_doc/repository-{request.user}/trad_fr{i}.docx')

                                    folder_doc = f'Tsukiyomi_doc/repository-{request.user}'
                                    merged_doc = Document()
                                    # Ne fusionner que les pages de ce PDF, dans leur ordre numérique.
                                    for page_index in range(len(pages)):
                                        docu = Document(os.path.join(folder_doc, f'trad_fr{page_index}.docx'))
                                        for element in docu.element.body:
                                            merged_doc.element.body.append(element)
                                    merged_doc.save(f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.docx')
                                    #convert(f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.docx', f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.pdf')
                                    mail_user = DocFile.user.email

                                            #transfert des fichiers traduits (.docx) sur la boite mail de l'utilisateur
                                            #le code ici
                                    print(f'soumission du fichier traité sur la boite mail {mail_user}')
                                    print("Envoie du fichier en piece jointe ...")
                                    pdf_traduit_final = f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.docx'

                                    email = EmailMessage(
                                        subject = f"Votre fichier de langue source {lang_select_pdf} traduit en Français",
                                        body = "Veuillez trouver ci-joint votre fichier traduit par TSUKIYOMI",
                                        from_email= settings.DEFAULT_FROM_EMAIL,
                                        to= [mail_user],
                                    
                                    )
                                    email.attach_file(pdf_traduit_final)
                                    email.send(fail_silently=False)
                                    print(f"Fichier transmis avec succès pour le compte {mail_user}")



                                           

                                            
                                        
                                    return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                                'text' : translated_fr
                                            })
                                #########################################################################################################
                                elif lang_select_pdf == 'italien' or lang_select_pdf == 'Italien':
                                    a = DocFile.button_televerse.path

                                    os.makedirs(f'media_upload/media/mediaby{request.user}', exist_ok=True)
                                    os.makedirs(f'Tsukiyomi_doc/repository-{request.user}', exist_ok=True)

                                    pages = convert_from_path(a, dpi=300, output_folder= f'media_upload/media/mediaby{request.user}')

                                    #extraction du text de chaque page
                                    for i, page in enumerate(pages):
                                        text = pytesseract.image_to_string(page, lang='ita', config=config)
                                        if text == '' or text == None:
                                            text = "aucun text détecté ..."
                                            return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                                'text' : text
                                            })
                                        else:
                                            #traduction des pages convertis en image en francais
                                            #code pour traduire en francais le text extrait
                                            translated_fr = GoogleTranslator(source='it', target='fr').translate(text, timeout=10)
                                            #translated_fr = argostranslate.translate.translate(text, "en", "fr")
                                            doc = Document()
                                            doc.add_heading('TRADUIT PAR ZENIA')
                                            doc.add_paragraph(translated_fr)

                                            print(f"un nouveau dossier pour l'utilisateur {request.user} sera crée ...")
                                            
                                            doc.save(f'Tsukiyomi_doc/repository-{request.user}/trad_fr{i}.docx')

                                    folder_doc = f'Tsukiyomi_doc/repository-{request.user}'
                                    merged_doc = Document()
                                    # Ne fusionner que les pages de ce PDF, dans leur ordre numérique.
                                    for page_index in range(len(pages)):
                                        docu = Document(os.path.join(folder_doc, f'trad_fr{page_index}.docx'))
                                        for element in docu.element.body:
                                            merged_doc.element.body.append(element)
                                    merged_doc.save(f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.docx')
                                    #convert(f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.docx', f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.pdf')
                                    mail_user = DocFile.user.email

                                            #transfert des fichiers traduits (.docx) sur la boite mail de l'utilisateur
                                            #le code ici
                                    print(f'soumission du fichier traité sur la boite mail {mail_user}')
                                    print("Envoie du fichier en piece jointe ...")
                                    pdf_traduit_final = f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.docx'

                                    email = EmailMessage(
                                        subject = f"Votre fichier de langue source {lang_select_pdf} traduit en Français",
                                        body = "Veuillez trouver ci-joint votre fichier traduit par TSUKIYOMI",
                                        from_email= settings.DEFAULT_FROM_EMAIL,
                                        to= [mail_user],
                                    
                                    )
                                    email.attach_file(pdf_traduit_final)
                                    email.send(fail_silently=False)
                                    print(f"Fichier transmis avec succès pour le compte {mail_user}")
                                    


                                           

                                            
                                        
                                    return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                                'text' : translated_fr
                                            })
                                ##########################################################################################################
                                elif lang_select_pdf == 'japonais' or lang_select_pdf == 'Japonais':
                                    a = DocFile.button_televerse.path

                                    os.makedirs(f'media_upload/media/mediaby{request.user}', exist_ok=True)
                                    os.makedirs(f'Tsukiyomi_doc/repository-{request.user}', exist_ok=True)

                                    pages = convert_from_path(a, dpi=300, output_folder= f'media_upload/media/mediaby{request.user}')

                                    #extraction du text de chaque page
                                    for i, page in enumerate(pages):
                                        text = pytesseract.image_to_string(page, lang='jpn', config=config)
                                        if text == '' or text == None:
                                            text = "aucun text détecté ..."
                                            return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                                'text' : text
                                            })
                                        else:
                                            #traduction des pages convertis en image en francais
                                            #code pour traduire en francais le text extrait
                                            translated_fr = GoogleTranslator(source='ja', target='fr').translate(text, timeout=10)
                                            #translated_fr = argostranslate.translate.translate(text, "en", "fr")
                                            doc = Document()
                                            doc.add_heading('TRADUIT PAR ZENIA')
                                            doc.add_paragraph(translated_fr)

                                            print(f"un nouveau dossier pour l'utilisateur {request.user} sera crée ...")
                                            
                                            doc.save(f'Tsukiyomi_doc/repository-{request.user}/trad_fr{i}.docx')

                                    folder_doc = f'Tsukiyomi_doc/repository-{request.user}'
                                    merged_doc = Document()
                                    # Ne fusionner que les pages de ce PDF, dans leur ordre numérique.
                                    for page_index in range(len(pages)):
                                        docu = Document(os.path.join(folder_doc, f'trad_fr{page_index}.docx'))
                                        for element in docu.element.body:
                                            merged_doc.element.body.append(element)
                                    merged_doc.save(f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.docx')
                                    #convert(f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.docx', f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.pdf')
                                    mail_user = DocFile.user.email

                                            #transfert des fichiers traduits (.docx) sur la boite mail de l'utilisateur
                                            #le code ici
                                    print(f'soumission du fichier traité sur la boite mail {mail_user}')
                                    
                                    print("Envoie du fichier en piece jointe ...")
                                    pdf_traduit_final = f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.docx'

                                    email = EmailMessage(
                                        subject = f"Votre fichier de langue source {lang_select_pdf} traduit en Français",
                                        body = "Veuillez trouver ci-joint votre fichier traduit par TSUKIYOMI",
                                        from_email= settings.DEFAULT_FROM_EMAIL,
                                        to= [mail_user],
                                    
                                    )
                                    email.attach_file(pdf_traduit_final)
                                    email.send(fail_silently=False)
                                    print(f"Fichier transmis avec succès pour le compte {mail_user}")

                                           

                                            
                                        
                                    return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                                'text' : translated_fr
                                            })
                                #############################################################################################################
                                elif lang_select_pdf == 'espagnol' or lang_select_pdf == 'Espagnol':
                                    a = DocFile.button_televerse.path

                                    os.makedirs(f'media_upload/media/mediaby{request.user}', exist_ok=True)
                                    os.makedirs(f'Tsukiyomi_doc/repository-{request.user}', exist_ok=True)

                                    pages = convert_from_path(a, dpi=300, output_folder= f'media_upload/media/mediaby{request.user}')

                                    #extraction du text de chaque page
                                    for i, page in enumerate(pages):
                                        text = pytesseract.image_to_string(page, lang='spa', config=config)
                                        if text == '' or text == None:
                                            text = "aucun text détecté ..."
                                            return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                                'text' : text
                                            })
                                        else:
                                            #traduction des pages convertis en image en francais
                                            #code pour traduire en francais le text extrait
                                            translated_fr = GoogleTranslator(source='es', target='fr').translate(text, timeout=10)
                                            #translated_fr = argostranslate.translate.translate(text, "en", "fr")
                                            doc = Document()
                                            doc.add_heading('TRADUIT PAR ZENIA')
                                            doc.add_paragraph(translated_fr)

                                            print(f"un nouveau dossier pour l'utilisateur {request.user} sera crée ...")
                                            
                                            doc.save(f'Tsukiyomi_doc/repository-{request.user}/trad_fr{i}.docx')

                                    folder_doc = f'Tsukiyomi_doc/repository-{request.user}'
                                    merged_doc = Document()
                                    # Ne fusionner que les pages de ce PDF, dans leur ordre numérique.
                                    for page_index in range(len(pages)):
                                        docu = Document(os.path.join(folder_doc, f'trad_fr{page_index}.docx'))
                                        for element in docu.element.body:
                                            merged_doc.element.body.append(element)
                                    merged_doc.save(f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.docx')
                                    #convert(f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.docx', f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.pdf')
                                    mail_user = DocFile.user.email

                                            #transfert des fichiers traduits (.docx) sur la boite mail de l'utilisateur
                                            #le code ici
                                    print(f'soumission du fichier traité sur la boite mail {mail_user}')
                                    print("Envoie du fichier en piece jointe ...")
                                    pdf_traduit_final = f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.docx'

                                    email = EmailMessage(
                                        subject = f"Votre fichier de langue source {lang_select_pdf} traduit en Français",
                                        body = "Veuillez trouver ci-joint votre fichier traduit par TSUKIYOMI",
                                        from_email= settings.DEFAULT_FROM_EMAIL,
                                        to= [mail_user],
                                    
                                    )
                                    email.attach_file(pdf_traduit_final)
                                    email.send(fail_silently=False)
                                    print(f"Fichier transmis avec succès pour le compte {mail_user}")
                                    


                                           

                                            
                                        
                                    return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                                'text' : translated_fr
                                            })
                                ############################################################################################################
                                elif lang_select_pdf == 'chinois' or lang_select_pdf == 'Chinois':
                                    a = DocFile.button_televerse.path

                                    os.makedirs(f'media_upload/media/mediaby{request.user}', exist_ok=True)
                                    os.makedirs(f'Tsukiyomi_doc/repository-{request.user}', exist_ok=True)

                                    pages = convert_from_path(a, dpi=300, output_folder= f'media_upload/media/mediaby{request.user}')

                                    #extraction du text de chaque page
                                    for i, page in enumerate(pages):
                                        text = pytesseract.image_to_string(page, lang='chi_tra', config=config)
                                        if text == '' or text == None:
                                            text = "aucun text détecté ..."
                                            return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                                'text' : text
                                            })
                                        else:
                                            #traduction des pages convertis en image en francais
                                            #code pour traduire en francais le text extrait
                                            translated_fr = GoogleTranslator(source='zh-TW', target='fr').translate(text, timeout=10)
                                            #translated_fr = argostranslate.translate.translate(text, "en", "fr")
                                            doc = Document()
                                            doc.add_heading('TRADUIT PAR ZENIA')
                                            doc.add_paragraph(translated_fr)

                                            print(f"un nouveau dossier pour l'utilisateur {request.user} sera crée ...")
                                            
                                            doc.save(f'Tsukiyomi_doc/repository-{request.user}/trad_fr{i}.docx')

                                    folder_doc = f'Tsukiyomi_doc/repository-{request.user}'
                                    merged_doc = Document()
                                    # Ne fusionner que les pages de ce PDF, dans leur ordre numérique.
                                    for page_index in range(len(pages)):
                                        docu = Document(os.path.join(folder_doc, f'trad_fr{page_index}.docx'))
                                        for element in docu.element.body:
                                            merged_doc.element.body.append(element)
                                    merged_doc.save(f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.docx')
                                    #convert(f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.docx', f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.pdf')
                                    mail_user = DocFile.user.email

                                            #transfert des fichiers traduits (.docx) sur la boite mail de l'utilisateur
                                            #le code ici
                                    print(f'soumission du fichier traité sur la boite mail {mail_user}')
                                    print("Envoie du fichier en piece jointe ...")
                                    pdf_traduit_final = f'Tsukiyomi_doc/repository-{request.user}/trad_fusion_{request.user}.docx'

                                    email = EmailMessage(
                                        subject = f"Votre fichier de langue source {lang_select_pdf} traduit en Français",
                                        body = "Veuillez trouver ci-joint votre fichier traduit par TSUKIYOMI",
                                        from_email= settings.DEFAULT_FROM_EMAIL,
                                        to= [mail_user],
                                    
                                    )
                                    email.attach_file(pdf_traduit_final)
                                    email.send(fail_silently=False)
                                    print(f"Fichier transmis avec succès pour le compte {mail_user}")
                                    


                                           

                                            
                                        
                                    return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                                'text' : translated_fr
                                            })





                            else:
                                print("le quota a depassé la limite de page pour le traitement...")
                                print("vous ne pourrez pas téléverser votre fichier...")
                                msg_error_limite_page_pdf = "[En mode Payant vous ne pouvez téléverser que des fichiers PDF de moins de 30 pages ]"
                                return render(request, 'tsukiyomi_app/televerse_page.html', context={
                                'msg_error_televerse' : msg_error_limite_page_pdf
                        }
                        )

                           
                            
                    else:
                        msg_error_televerse = "[ Limite de téléversement des fichiers PDF atteinte. vous n'avez droit qu'à 10 fichiers pdf téléversés ...] "     
                        return render(request, 'tsukiyomi_app/televerse_page.html', context={
                                'msg_error_televerse' : msg_error_televerse
                        }
                        )
                                        
                
                    
                elif (tf == 'Image') and (str(ef).endswith('.jpg') or str(ef).endswith('.png')):
                     print("Traitement fichier Image ...")
                     
                     #traitement des fichiers image
                     #verification de la limite de téléversement

                     
                     existing_count_img = ALL_DOC.filter(user=request.user, type_file="Image").count()
                   
                        
                     if (existing_count_img <= 14 ):
                        DocFile = DocForm.save(commit=False)
                        if request.user.is_authenticated:
                            DocFile.user = request.user
                            print(f"etat de connexion : {request.user.is_authenticated}")
                            print(f"type d'utilisateur : {request.user}")
                            DocFile.save()

                            #le traitement et la conversion se font ici
                            with Image.open(DocFile.button_televerse.path) as img:
                                lang_select = DocForm.cleaned_data['type_language']

                                #bloc gestion langue francaise
                                if lang_select == 'français' or lang_select == 'Français':
                                    
                                    os.makedirs(f'Tsukiyomi_doc/repositoryImg-{request.user}', exist_ok=True)
                                    text = pytesseract.image_to_string(img, lang='fra', config=config)
                                    if text == '' or text == None:
                                        text = "aucun texte détecté ..."
                                        return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                        'text' : text
                                         })
                                    else:
                                        

                                        #code de traduction du texte
                                        translated_fr = GoogleTranslator(source='fr', target='fr').translate(text, timeout=10)
                                            #translated_fr = argostranslate.translate.translate(text, "en", "fr")
                                        doc = Document()
                                        doc.add_heading('TRADUIT PAR ZENIA')
                                        doc.add_paragraph(translated_fr)
                                        
                                        print("le dossier Tsukiyomi_doc n'existe pas")
                                        
                                        doc.save(f'Tsukiyomi_doc/repositoryImg-{request.user}/trad_fr.docx')
                                        #convert('Tsukiyomi_doc/trad_fr.docx', 'Tsukiyomi_doc/trad_fr.pdf')
                                        mail_user = DocFile.user.email
                                            
                                            
                                        #transfert des fichiers traduits (.docx, .pdf) sur la boite mail de l'utilisateur
                                        #le code ici
                                        print(f'soumission du fichier traité sur la boite mail {mail_user}')
                                        print("Envoie du fichier en piece jointe ...")
                                        img_traduit_final = f'Tsukiyomi_doc/repositoryImg-{request.user}/trad_fr.docx'

                                        email = EmailMessage(
                                            subject = f"Votre fichier de langue source {lang_select} traduit en Français",
                                            body = "Veuillez trouver ci-joint votre fichier traduit par TSUKIYOMI",
                                            from_email= settings.DEFAULT_FROM_EMAIL,
                                            to= [mail_user],
                                        
                                        )
                                        email.attach_file(img_traduit_final)
                                        email.send(fail_silently=False)
                                        print(f"Fichier transmis avec succès pour le compte {mail_user}")


                                        return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                        'text' : translated_fr


                                        })
                                    ############################################################################################
                                    
                                elif lang_select == 'anglais' or lang_select == 'Anglais':
                                    os.makedirs(f'Tsukiyomi_doc/repositoryImg-{request.user}', exist_ok=True)
                                    text = pytesseract.image_to_string(img, lang='eng')
                                    if text == '' or text == None:
                                        text = "aucun texte détecté ..."
                                        return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                        'text' : text
                                         })
                                    else:
                                        #code de traduction du texte
                                        translated_fr = GoogleTranslator(source='en', target='fr').translate(text, timeout=10)
                                            #translated_fr = argostranslate.translate.translate(text, "en", "fr")
                                        doc = Document()
                                        doc.add_heading('TRADUIT PAR ZENIA')
                                        doc.add_paragraph(translated_fr)
                                        
                                        print("le dossier Tsukiyomi_doc n'existe pas")
                                        
                                        doc.save(f'Tsukiyomi_doc/repositoryImg-{request.user}/trad_fr.docx')
                                        #convert('Tsukiyomi_doc/trad_fr.docx', 'Tsukiyomi_doc/trad_fr.pdf')
                                        mail_user = DocFile.user.email
                                            
                                            
                                        #transfert des fichiers traduits (.docx, .pdf) sur la boite mail de l'utilisateur
                                        #le code ici
                                        print(f'soumission du fichier traité sur la boite mail {mail_user}')
                                        print("Envoie du fichier en piece jointe ...")
                                        img_traduit_final = f'Tsukiyomi_doc/repositoryImg-{request.user}/trad_fr.docx'

                                        email = EmailMessage(
                                            subject = f"Votre fichier de langue source {lang_select} traduit en Français",
                                            body = "Veuillez trouver ci-joint votre fichier traduit par TSUKIYOMI",
                                            from_email= settings.DEFAULT_FROM_EMAIL,
                                            to= [mail_user],
                                        
                                        )
                                        email.attach_file(img_traduit_final)
                                        email.send(fail_silently=False)
                                        print(f"Fichier transmis avec succès pour le compte {mail_user}")


                                        #apres soumission des fichiers à l'utilisateur via sa boite mail
                                        #suppression des fichiers sur le serveur
                                        # folder_tsukiyomi_doc = 'Tsukiyomi_doc'
                                        # shutil.rmtree(folder_tsukiyomi_doc)
                                       
                                        

                                        
                                        #suppresion des fichiers images stockées sur le serveur

                                        # folder_image_televerse = 'media_upload/media'
                                        # for fit in os.listdir(folder_image_televerse):
                                        #     if fit.endswith('.png') or fit.endswith('jpg'):
                                        #         path_file = os.path.join(folder_image_televerse, fit)
                                        #         os.remove(path_file)
                                    
                                        return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                        'text' : translated_fr


                                        })
                                    
                                elif lang_select == 'japonais' or lang_select == 'Japonais':
                                    os.makedirs(f'Tsukiyomi_doc/repositoryImg-{request.user}', exist_ok=True)
                                    text = pytesseract.image_to_string(img, lang='jpn')
                                    if text == '' or text == None:
                                        text = "aucun texte détecté ..."
                                        return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                        'text' : text
                                         })
                                    else:
                                        #code de traduction du texte
                                        translated_fr = GoogleTranslator(source='ja', target='fr').translate(text, timeout=10)
                                            #translated_fr = argostranslate.translate.translate(text, "en", "fr")
                                        doc = Document()
                                        doc.add_heading('TRADUIT PAR ZENIA')
                                        doc.add_paragraph(translated_fr)
                                        
                                        print("le dossier Tsukiyomi_doc n'existe pas")
                                       
                                        doc.save(f'Tsukiyomi_doc/repositoryImg-{request.user}/trad_fr.docx')
                                        #convert('Tsukiyomi_doc/trad_fr.docx', 'Tsukiyomi_doc/trad_fr.pdf')
                                        mail_user = DocFile.user.email
                                            
                                            
                                        #transfert des fichiers traduits (.docx, .pdf) sur la boite mail de l'utilisateur
                                        #le code ici
                                        print(f'soumission du fichier traité sur la boite mail {mail_user}')
                                        print("Envoie du fichier en piece jointe ...")
                                        img_traduit_final = f'Tsukiyomi_doc/repositoryImg-{request.user}/trad_fr.docx'

                                        email = EmailMessage(
                                            subject = f"Votre fichier de langue source {lang_select} traduit en Français",
                                            body = "Veuillez trouver ci-joint votre fichier traduit par TSUKIYOMI",
                                            from_email= settings.DEFAULT_FROM_EMAIL,
                                            to= [mail_user],
                                        
                                        )
                                        email.attach_file(img_traduit_final)
                                        email.send(fail_silently=False)
                                        print(f"Fichier transmis avec succès pour le compte {mail_user}")


                                        #apres soumission des fichiers à l'utilisateur via sa boite mail
                                        #suppression des fichiers sur le serveur
                                        # folder_tsukiyomi_doc = 'Tsukiyomi_doc'
                                        # shutil.rmtree(folder_tsukiyomi_doc)

                                        
                                        #suppresion des fichiers images stockées sur le serveur

                                        # folder_image_televerse = 'media_upload/media'
                                        # for fit in os.listdir(folder_image_televerse):
                                        #     if fit.endswith('.png') or fit.endswith('jpg'):
                                        #         path_file = os.path.join(folder_image_televerse, fit)
                                        #         os.remove(path_file)
                                    
                                        return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                        'text' : translated_fr


                                        })
                                    

                                elif lang_select == 'espagnol' or lang_select == 'Espagnol':
                                    os.makedirs(f'Tsukiyomi_doc/repositoryImg-{request.user}', exist_ok=True)
                                    text = pytesseract.image_to_string(img, lang='spa')
                                    if text == '' or text == None:
                                        text = "aucun texte détecté ..."
                                        return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                        'text' : text
                                         })
                                    else:
                                        #code de traduction du texte
                                        translated_fr = GoogleTranslator(source='es', target='fr').translate(text, timeout=10)
                                            #translated_fr = argostranslate.translate.translate(text, "en", "fr")
                                        doc = Document()
                                        doc.add_heading('TRADUIT PAR ZENIA')
                                        doc.add_paragraph(translated_fr)
                                        
                                        print("le dossier Tsukiyomi_doc n'existe pas")
                                        
                                        doc.save(f'Tsukiyomi_doc/repositoryImg-{request.user}/trad_fr.docx')
                                        #convert('Tsukiyomi_doc/trad_fr.docx', 'Tsukiyomi_doc/trad_fr.pdf')
                                        mail_user = DocFile.user.email
                                            
                                            
                                        #transfert des fichiers traduits (.docx, .pdf) sur la boite mail de l'utilisateur
                                        #le code ici
                                        print(f'soumission du fichier traité sur la boite mail {mail_user}')
                                        print("Envoie du fichier en piece jointe ...")
                                        img_traduit_final = f'Tsukiyomi_doc/repositoryImg-{request.user}/trad_fr.docx'

                                        email = EmailMessage(
                                            subject = f"Votre fichier de langue source {lang_select} traduit en Français",
                                            body = "Veuillez trouver ci-joint votre fichier traduit par TSUKIYOMI",
                                            from_email= settings.DEFAULT_FROM_EMAIL,
                                            to= [mail_user],
                                        
                                        )
                                        email.attach_file(img_traduit_final)
                                        email.send(fail_silently=False)
                                        print(f"Fichier transmis avec succès pour le compte {mail_user}")


                                        #apres soumission des fichiers à l'utilisateur via sa boite mail
                                        #suppression des fichiers sur le serveur
                                        # folder_tsukiyomi_doc = 'Tsukiyomi_doc'
                                        # shutil.rmtree(folder_tsukiyomi_doc)
                                        

                                        
                                        # #suppresion des fichiers images stockées sur le serveur

                                        # folder_image_televerse = 'media_upload/media'
                                        # for fit in os.listdir(folder_image_televerse):
                                        #     if fit.endswith('.png') or fit.endswith('jpg'):
                                        #         path_file = os.path.join(folder_image_televerse, fit)
                                        #         os.remove(path_file)
                                    
                                        return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                        'text' : translated_fr


                                        })
                                
                                elif lang_select == 'chinois' or lang_select == 'Chinois':
                                    os.makedirs(f'Tsukiyomi_doc/repositoryImg-{request.user}', exist_ok=True)
                                    text = pytesseract.image_to_string(img, lang='chi_tra')
                                    if text == '' or text == None:
                                        text = "aucun texte détecté ..."
                                        return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                        'text' : text
                                         })
                                    else:
                                        #code de traduction du texte
                                        translated_fr = GoogleTranslator(source='zh-TW', target='fr').translate(text, timeout=10)
                                            #translated_fr = argostranslate.translate.translate(text, "en", "fr")
                                        doc = Document()
                                        doc.add_heading('TRADUIT PAR ZENIA')
                                        doc.add_paragraph(translated_fr)
                                        
                                        print("le dossier Tsukiyomi_doc n'existe pas")
                                        
                                        doc.save(f'Tsukiyomi_doc/repositoryImg-{request.user}/trad_fr.docx')
                                        #convert('Tsukiyomi_doc/trad_fr.docx', 'Tsukiyomi_doc/trad_fr.pdf')
                                        mail_user = DocFile.user.email
                                            
                                            
                                        #transfert des fichiers traduits (.docx, .pdf) sur la boite mail de l'utilisateur
                                        #le code ici
                                        print(f'soumission du fichier traité sur la boite mail {mail_user}')
                                        print("Envoie du fichier en piece jointe ...")
                                        img_traduit_final = f'Tsukiyomi_doc/repositoryImg-{request.user}/trad_fr.docx'

                                        email = EmailMessage(
                                            subject = f"Votre fichier de langue source {lang_select} traduit en Français",
                                            body = "Veuillez trouver ci-joint votre fichier traduit par TSUKIYOMI",
                                            from_email= settings.DEFAULT_FROM_EMAIL,
                                            to= [mail_user],
                                        
                                        )
                                        email.attach_file(img_traduit_final)
                                        email.send(fail_silently=False)
                                        print(f"Fichier transmis avec succès pour le compte {mail_user}")


                                        #apres soumission des fichiers à l'utilisateur via sa boite mail
                                        #suppression des fichiers sur le serveur
                                        # folder_tsukiyomi_doc = 'Tsukiyomi_doc'
                                        # shutil.rmtree(folder_tsukiyomi_doc)
                                        

                                        
                                        # #suppresion des fichiers images stockées sur le serveur

                                        # folder_image_televerse = 'media_upload/media'
                                        # for fit in os.listdir(folder_image_televerse):
                                        #     if fit.endswith('.png') or fit.endswith('jpg'):
                                        #         path_file = os.path.join(folder_image_televerse, fit)
                                        #         os.remove(path_file)
                                    
                                        return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                        'text' : translated_fr


                                        })
                                    
                                
                                elif lang_select == 'italien' or lang_select == 'Italien':
                                    os.makedirs(f'Tsukiyomi_doc/repositoryImg-{request.user}', exist_ok=True)
                                    text = pytesseract.image_to_string(img, lang='ita')
                                    if text == '' or text == None:
                                        text = "aucun texte détecté ..."
                                        return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                        'text' : text
                                         })
                                    else:
                                        #code de traduction du texte
                                        translated_fr = GoogleTranslator(source='it', target='fr').translate(text, timeout=10)
                                            #translated_fr = argostranslate.translate.translate(text, "en", "fr")
                                        doc = Document()
                                        doc.add_heading('TRADUIT PAR ZENIA')
                                        doc.add_paragraph(translated_fr)
                                        
                                        print("le dossier Tsukiyomi_doc n'existe pas")
                                        
                                        doc.save(f'Tsukiyomi_doc/repositoryImg-{request.user}/trad_fr.docx')
                                        #convert('Tsukiyomi_doc/trad_fr.docx', 'Tsukiyomi_doc/trad_fr.pdf')
                                        mail_user = DocFile.user.email
                                            
                                            
                                        #transfert des fichiers traduits (.docx, .pdf) sur la boite mail de l'utilisateur
                                        #le code ici
                                        print(f'soumission du fichier traité sur la boite mail {mail_user}')
                                        print("Envoie du fichier en piece jointe ...")
                                        img_traduit_final = f'Tsukiyomi_doc/repositoryImg-{request.user}/trad_fr.docx'

                                        email = EmailMessage(
                                            subject = f"Votre fichier de langue source {lang_select} traduit en Français",
                                            body = "Veuillez trouver ci-joint votre fichier traduit par TSUKIYOMI",
                                            from_email= settings.DEFAULT_FROM_EMAIL,
                                            to= [mail_user],
                                        
                                        )
                                        email.attach_file(img_traduit_final)
                                        email.send(fail_silently=False)
                                        print(f"Fichier transmis avec succès pour le compte {mail_user}")


                                        #apres soumission des fichiers à l'utilisateur via sa boite mail
                                        #suppression des fichiers sur le serveur
                                        # folder_tsukiyomi_doc = 'Tsukiyomi_doc'
                                        # shutil.rmtree(folder_tsukiyomi_doc)
                                        

                                        
                                        # #suppresion des fichiers images stockées sur le serveur

                                        # folder_image_televerse = 'media_upload/media'
                                        # for fit in os.listdir(folder_image_televerse):
                                        #     if fit.endswith('.png') or fit.endswith('jpg'):
                                        #         path_file = os.path.join(folder_image_televerse, fit)
                                        #         os.remove(path_file)
                                    
                                        return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                        'text' : translated_fr


                                        })
                                    
                                
                                
                                

                                else:
                                    text = "Cette langue n'est pas prise en compte pour le moment..."                                                          
                                    #print("aucun text detecté")
                                    return render(request, 'tsukiyomi_app/succes_uploadfile.html', context={
                                        'text' : text


                                        })
                                    



                           # return redirect('pdf_or_image')
                        else:
                            print(f"etat de connexion : {request.user.is_authenticated}")
                            print(f"type d'utilisateur : {request.user}")
                                
                            return HttpResponseForbidden("Vous devez vous connecter.")
                    
                    
                     else:
                        msg_error_televerse = "[ Limite de téléversement des fichiers Image atteinte ]"
                           
                        return render(request, 'tsukiyomi_app/televerse_page.html', context={
                                'msg_error_televerse' : msg_error_televerse
                            })



                else:
                    msg_error_extension_file = "le type et l'extension de votre fichier téléversé ne correspondent pas ..."
                
                    return render(request, 'tsukiyomi_app/televerse_page.html', context={
                        'msg_error_extension_file' : msg_error_extension_file
                    })
    
                
                
                
        
            
        else:
            DocForm = DocumentForm(prefix="pi")
            return render(request, 'tsukiyomi_app/televerse_page.html', context={
                'DocForm': DocForm
            })
        
    return render(request, 'tsukiyomi_app/televerse_page.html', context={
                'DocForm': DocForm,
                'notif_stage_process' : notif_stage_process
            })




#---------------- VUE QUI REDIRIGE VERS LA METHODE DE TELEVERSEMENT REQUISE EN FONCTION DU TYPE D'ABONNEMENT

@login_required
def return_type_televerse(request):
    if request.user.state_abonnement == True:
        return redirect('name_televerse_url_paid')
    else:
        return redirect('name_televerse_url_free')
