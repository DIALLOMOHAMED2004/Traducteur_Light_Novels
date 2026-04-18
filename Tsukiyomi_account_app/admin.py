from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import UserTsukiyomi

class AdminUser(admin.ModelAdmin):
    list_display = ('username', 'email', 'state', 'state_abonnement')
    search_fields = ('username',)
    list_editable = ('email',)


admin.site.register(UserTsukiyomi, AdminUser)


