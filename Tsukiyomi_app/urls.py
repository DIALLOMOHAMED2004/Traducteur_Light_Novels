from django.urls import path
from .views import reindex, get_televerse, subscribe_view, clear_media_data, check_table_users
from .views_abonnement import check_abonnement_free, check_abonnement_paid

urlpatterns = [

    path("reindex", reindex, name="reindex"),
    path("tele/", get_televerse, name="televerse_url"),
    # Compatibilité des anciens liens/POST et de leurs refus d'accès, sans second pipeline.
    path("tele_paid/", check_abonnement_paid(get_televerse), name="name_televerse_url_paid"),
    path("tele_free/", check_abonnement_free(get_televerse), name="name_televerse_url_free"),
    
    
    #path("return_pdf_or_image/", return_pdf_or_image_parse, name="pdf_or_image"),
    #path("parse_pdf01/", parse_doc_pdf, name="parse_pdf"),
    #path("parse_image01/", parse_image, name="parse_image"),
    path("subscrib2/", subscribe_view, name="subscrib_newsletter"),
    path("clear_media/", clear_media_data, name="clear_media_name"),
    path("check_table_use/", check_table_users, name="check_table"),
    
]
