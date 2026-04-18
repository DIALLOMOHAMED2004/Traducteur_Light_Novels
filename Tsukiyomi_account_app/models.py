from django.db import models
from django.contrib.auth.models import AbstractUser





class UserTsukiyomi(AbstractUser):
    
    password = models.CharField(max_length=300, null=True, verbose_name='Mot de passe 1')
    password2 = models.CharField(max_length=300, null=True, verbose_name='Mot de passe 2')
    state = models.BooleanField(default=False)
    state_abonnement = models.BooleanField(default=False)
    #tel_usertsukiyomi = models.CharField(max_length=300, blank=False, verbose_name='Téléphone')


    def __str__(self):
        return self.username




    



