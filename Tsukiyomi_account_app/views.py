from django.shortcuts import render, redirect, HttpResponse
from django.contrib.auth import logout, login, authenticate, get_user_model
from .forms import LoginFormUser, CreateFormUser
from .models import UserTsukiyomi


User = get_user_model()




#vue de la creation de compte

def register(request):
   
    if len(request.POST) > 0 and 'profileType' in request.POST:
        cuf = CreateFormUser(prefix="ut")

        if request.POST['profileType'] == 'utilisateur':
            cuf = CreateFormUser(request.POST, prefix="ut")

            if cuf.is_valid():
                
                
                msg,username,email,password  = cuf.hash_password()
                if msg == "Les mots de passe correspondent...":
                    #cuf.save(commit=True)
                    
                    #user = get_user_model()

                    user = User.objects.create_user(username=username, email=email,password=password)
                    login(request, user)
                    return redirect('login_view')
                else:
                     msgerror = "Les mots de passe ne correspondent pas..."
                     cuf = CreateFormUser()
                     return render(request, "tsukiyomi_account_app/register.html", context={
                        'cuf':cuf,
                        'msgerror': msgerror
                    })
                    
        
        
    cuf = CreateFormUser(prefix="ut")
    return render(request, "tsukiyomi_account_app/register.html", context={
            'cuf':cuf
        })




#vue de l'authentification
def login_view(request):
    luf = LoginFormUser()
    error_msg = None
    state_connexion = None

    if request.method == 'POST':
        luf = LoginFormUser(request.POST)
        if luf.is_valid():
            username = luf.cleaned_data["username"]
            password = luf.cleaned_data["password"]
            
            user = authenticate(request,username=username, password=password)

            if user:
                login(request, user)
                print(f"utilisateur : {request.user}")
                redirect('reindex')
            else:
                error_msg = "Non correspondance des informations de connexion..."
                print(f"utilisateur : {request.user}")
                state_connexion = f"etat de la connexion : {request.user} - Utilisateur non connecté"
                
    return render(request, 'tsukiyomi_account_app/login.html', context={
        'luf':luf,
        'error_msg':error_msg,
        'state_connexion': state_connexion
    })


    


def deconnexion(request):
    logout(request)
    print(f'statut utilisateur en deconnexion : {request.user}')
    return redirect('login_view')
