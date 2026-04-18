from django import forms
from .models import DocFile, Subscriber

class DocumentForm(forms.ModelForm):
    class Meta:
        model = DocFile
        fields = ['type_file', 'type_language', 'button_televerse']
        exclude = ['user','uploaded_at']
        widgets = {
            'type_file': forms.Select(attrs={'style': 'background-color: RGB(250, 250, 250);border-color: RGB(111, 57, 11); color: RGB(111, 57, 11)','class': 'form-control for-control-user form-livedoc-control'}),
            'type_language': forms.Select(attrs={'style': 'background-color: RGB(250, 250, 250);border-color: RGB(111, 57, 11); color: RGB(111, 57, 11)','class': 'form-control for-control-user form-livedoc-control'}),
            'button_televerse': forms.FileInput(attrs={'style': 'background-color: RGB(250, 250, 250);border-color: RGB(111, 57, 11); color: RGB(111, 57, 11)','class': 'form-control for-control-user form-livedoc-control'})
            
        }

    
class SubscribeForm(forms.ModelForm):
    class Meta:
        model = Subscriber
        fields = ['email']
        widgets = {
            'email': forms.EmailInput(attrs={'style': 'background-color: RGB(250, 250, 250);border-color: RGB(111, 57, 11); color: RGB(111, 57, 11)','class': 'form-control form-livedoc-control form-cta-control text-soft-primary', 'id': 'inputEmailCta', 'type': 'email', 'placeholder': 'Votre boite mail'})
            
            
        }

        labels = {
            'email' : ''
        }

       
        