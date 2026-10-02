from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required


#creation des wrapper pour les acces de televersement en fonction de l'etat d'abonnement

def check_abonnement_free(func):
    @login_required
    def wrapper(request, **kwargs):
        if request.user.state_abonnement == False:
            return func(request, **kwargs)
        else:
            print("Accès interdit pour un abonnement payant")
            return render(request, "tsukiyomi_app/error_abonnement_free.html")
            
    return wrapper


def check_abonnement_paid(func):
    @login_required
    def wrapper(request, **kwargs):
        if request.user.state_abonnement == True:
            return func(request, **kwargs)
        else:
            print("Accès interdit pour un abonnement gratuit")
            return render(request, "tsukiyomi_app/error_abonnement_payant.html")
    return wrapper
