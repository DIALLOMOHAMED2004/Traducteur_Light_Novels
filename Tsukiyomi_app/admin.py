from django.contrib import admin
from .models import DocFile, Subscriber
from django.urls import path, include
from django.contrib import messages
from django.shortcuts import redirect

admin.site.site_header = "TSUKIYOMI-ADMIN"

class AdminDocFile(admin.ModelAdmin):
    list_display = ('user', 'type_file', 'type_language', 'uploaded_at', 'button_televerse')
    search_fields = ('user',)
    list_editable = ('type_file',)

class AdminSubscriber(admin.ModelAdmin):
    list_display = ('email', 'date_subscribed')
    search_fields = ('email',)
    #list_editable = ('date_subscribed',)

# class MyAdminSite(admin.ModelAdmin):
#     def get_urls(self):
#         urls = super().get_urls()
#         urls += [
#             path('clear_media_name1/', include('tsukiyomi_app.urls'), name='clear_media_name')
#         ]
#         return urls
    

        


admin.site.register(DocFile, AdminDocFile)
admin.site.register(Subscriber, AdminSubscriber)



