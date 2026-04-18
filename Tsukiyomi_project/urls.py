
from django.contrib import admin
from django.urls import path, include
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf.urls.static import static
from django.conf import settings
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('clear_media_name1/', include('Tsukiyomi_app.urls'), name='clear_media_name'),


    #route pour la gestion de l'application Tsukiyomi_app
    path('indexpage/', include('Tsukiyomi_app.urls'), name='reindex'),
    path('televerse/', include('Tsukiyomi_app.urls'), name='televerse_url'),
    path('televerse_free_free/', include('Tsukiyomi_app.urls'), name='name_televerse_url_free'),
    path('televerse_free_paid/', include('Tsukiyomi_app.urls'), name='name_televerse_url_paid'),

    path('00001pdf_or_image/', include('Tsukiyomi_app.urls'), name='pdf_or_image'),
    path('0001pdf/', include('Tsukiyomi_app.urls'), name='parse_pdf'),
    path('0001image/', include('Tsukiyomi_app.urls'), name='parse_image'),
    path('check1111/', include('Tsukiyomi_app.urls'), name='checkDoc'),
    path('subscrib1/', include('Tsukiyomi_app.urls'), name="subscrib_newsletter"),
    path('chtable01/', include('Tsukiyomi_app.urls'), name='check_table'),


    #route pour la gestion des comptes
    path('registeruser/', include('Tsukiyomi_account_app.urls'), name="register"),
    path('logoutuser/', include('Tsukiyomi_account_app.urls'), name="deco"),
    path('loginuser/', include('Tsukiyomi_account_app.urls'), name="login_view"),


    #route pour les vues natives de django
    #path('accounts/login', include('django.contrib.auth.urls'),name='login'),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='tsukiyomi_account_app/login.html'), name='login'),

    
]


urlpatterns += staticfiles_urlpatterns()
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)