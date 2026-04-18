from django import forms
from django.forms import ModelForm
from .models import UserTsukiyomi
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model


#creation de formulaire d'authentification

class LoginFormUser(forms.Form):
    username = forms.CharField(label='', required=True,
                            widget = forms.TextInput(
                                attrs= {
                                    'id': 'inputName',
                                    'placeholder' : 'votre nom Utilisateur',
                                    'class' : 'form-control form-livedoc-control',
                                    'type': 'text',
                                    'style': 'border-color: RGB(111, 57, 11); background-color: RGB(250, 250, 250); color: RGB(111, 57, 11)'
                                }
                            ),max_length=300
                            )
                            
    password = forms.CharField(label='', required=True,
                               widget = forms.PasswordInput(
                                   attrs={
                                       'id': 'inputPassword',
                                       'placeholder':'votre mot de passe',
                                       'class' : 'form-control form-livedoc-control',
                                       'type': 'password',
                                       'style': 'border-color: RGB(111, 57, 11); background-color: RGB(250, 250, 250); color: RGB(111, 57, 11)'
                                      
                                       
                                   }
                               ),
                               max_length=300
                               )

    # def clean(self):
    #     cleaned_data = super(LoginFormUser, self).clean()
    #     username = cleaned_data.get("username")
    #     password = cleaned_data.get("password")


    #     #verification de la validité des 2 champs

    #     if username and password:
    #         #on cherche toute personne avec lequel le password
    #         #et le mail entrés dans le formulaire correspond dans 
    #         #la base de donnees

    #         result_user = UserTsukiyomi.objects.filter(username=username ,password=password)
    #         if len(result_user) != 1:
    #             raise forms.ValidationError("Mot de passe ou Utilisateur incorrecte")
    #     return cleaned_data 





class CreateFormUser(ModelForm):
    class Meta:
        model = UserTsukiyomi
        fields = ['username', 'password', 'password2', 'email']
        exclude = ('state',)
    
    
        
        
        widgets = {
            'username': forms.TextInput(attrs={'style': 'background-color: RGB(250, 250, 250);border-color: RGB(111, 57, 11); color: RGB(111, 57, 11)','id':'exampleFirstName',  'class' : 'form-control form-control-user form-livedoc-control','placeholder': 'Veuillez entrer un nom valide'}),
            #'prenom_UserTsukiyomi':forms.TextInput(attrs={ 'style': 'background-color: RGB(250, 250, 250);border-color: RGB(111, 57, 11); color: RGB(111, 57, 11)','id': 'exampleLastName','class' : 'form-control form-control-user form-livedoc-control','placeholder': 'Veuillez entrer un prenom valide'}),
            'password': forms.PasswordInput(attrs={'style': 'background-color: RGB(250, 250, 250);border-color: RGB(111, 57, 11); color: RGB(111, 57, 11)' ,'id': 'exampleInputPassword','class' : 'form-control form-control-user form-livedoc-control','placeholder': 'Veuillez entrer un mot de passe robuste'}),
            'password2': forms.PasswordInput(attrs={'style': 'background-color: RGB(250, 250, 250);border-color: RGB(111, 57, 11); color: RGB(111, 57, 11)' ,'id': 'exampleInputPassword','class' : 'form-control form-control-user form-livedoc-control','placeholder': 'Confirmation du mot de passe'}),
            'email': forms.EmailInput(attrs={'style': 'background-color: RGB(250, 250, 250);border-color: RGB(111, 57, 11); color: RGB(111, 57, 11)','id':'exampleInputEmail','class' : 'form-control form-control-user form-livedoc-control','placeholder': 'Veuillez entrer un mail valide'}),
            #'tel_usertsukiyomi': forms.TextInput(attrs={'style': 'background-color: RGB(250, 250, 250);border-color: RGB(111, 57, 11); color: RGB(111, 57, 11)','class' : 'form-control form-control-user form-livedoc-control','placeholder': 'Veuillez entrer un numéro valide : (+237 6XXX...)'}),

        } 

        labels = {
            'username':'',
            #'prenom_UserTsukiyomi':'',
            'password':'',
            'password2':'',
            'email':'',
            #'tel_usertsukiyomi':''


        }

    
    def hash_password(self):
            
            cleaned_data = super(CreateFormUser, self).clean()
            username = cleaned_data.get("username")
            password = cleaned_data.get("password")
            password2 = cleaned_data.get("password2")
            email = cleaned_data.get("email")
            #tel_usertsukiyomi = cleaned_data.get("tel_usertsukiyomi")


            if password == password2:
                
                msgerror = "Les mots de passe correspondent..."
                print(msgerror)
            else:
                msgerror = "Les mots de passe ne correspondent pas..."
                print(msgerror)
            return msgerror,username,email,password,
        
                
                

        





                            
    