from django.urls import path
from .views import reindex, get_televerse, subscribe_view, clear_media_data, check_table_users, get_televerse2, return_type_televerse

urlpatterns = [

    path("reindex", reindex, name="reindex"),
    path("tele/", return_type_televerse, name="televerse_url"),
    path("tele_paid/",  get_televerse2, name="name_televerse_url_paid"),
    path("tele_free/", get_televerse, name="name_televerse_url_free"),
    
    
    #path("return_pdf_or_image/", return_pdf_or_image_parse, name="pdf_or_image"),
    #path("parse_pdf01/", parse_doc_pdf, name="parse_pdf"),
    #path("parse_image01/", parse_image, name="parse_image"),
    path("subscrib2/", subscribe_view, name="subscrib_newsletter"),
    path("clear_media/", clear_media_data, name="clear_media_name"),
    path("check_table_use/", check_table_users, name="check_table"),
    
]