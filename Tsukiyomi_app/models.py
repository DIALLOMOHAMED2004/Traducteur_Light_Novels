from django.db import models
from django.conf import settings
from Tsukiyomi_account_app.models import UserTsukiyomi





TYPE_CHOICE_FILE = (

    ('PDF', 'pdf',),
    ('Image', 'image')

)

TYPE_CHOICE_LANGUAGE = (
    ('Italien', 'italien',),
    ('Chinois', 'chinois',),
    ('Français', 'français',),
    ('Japonais', 'japonais',),
    ('Anglais', 'anglais',),
    ('Espagnol', 'espagnol')
)

class DocFile(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    type_file = models.CharField(max_length=50, blank=False, choices=TYPE_CHOICE_FILE, verbose_name='Type de Fichier')
    type_language = models.CharField(max_length=60, blank=False, choices=TYPE_CHOICE_LANGUAGE, verbose_name='Langue du fichier source')
    button_televerse = models.FileField(upload_to=f'media', max_length=200, verbose_name='Téléverser votre fichier')
    uploaded_at = models.DateTimeField(auto_now_add=True, blank=True)
    
    

    def __str__(self):
        return f'Doc-{self.type_file}-{self.button_televerse.name}'
    


class Subscriber(models.Model):
    email = models.EmailField(unique=True)
    date_subscribed = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f" Newsletter-{self.email}"
        
