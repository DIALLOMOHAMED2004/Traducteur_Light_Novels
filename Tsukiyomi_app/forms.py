from django import forms
from pathlib import Path

from PIL import Image, UnidentifiedImageError
from PyPDF2 import PdfReader
from PyPDF2.errors import PdfReadError

from .models import DocFile, Subscriber


MAX_UPLOAD_SIZE = 20 * 1024 * 1024
MAX_IMAGE_DIMENSION = 20_000
MAX_IMAGE_PIXELS = 40_000_000


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

    def clean_button_televerse(self):
        """Rejeter les fichiers dangereux avant leur sauvegarde et leur traitement."""
        uploaded_file = self.cleaned_data['button_televerse']
        file_type = self.cleaned_data.get('type_file')
        extension = Path(uploaded_file.name).suffix

        if uploaded_file.size > MAX_UPLOAD_SIZE:
            raise forms.ValidationError("Le fichier ne doit pas dépasser 20 Mo.")

        if file_type == 'PDF':
            if extension not in ('.pdf', '.PDF'):
                raise forms.ValidationError("Le fichier sélectionné doit être un PDF.")

            try:
                page_count = len(PdfReader(uploaded_file).pages)
            except (PdfReadError, EOFError, OSError, ValueError) as error:
                raise forms.ValidationError("Le fichier PDF est invalide ou corrompu.") from error
            finally:
                uploaded_file.seek(0)

            if page_count == 0:
                raise forms.ValidationError("Le fichier PDF ne contient aucune page.")

        elif file_type == 'Image':
            if extension not in ('.jpg', '.png'):
                raise forms.ValidationError("L'image doit être au format JPG ou PNG.")

            try:
                with Image.open(uploaded_file) as image:
                    width, height = image.size
                    if (
                        width > MAX_IMAGE_DIMENSION
                        or height > MAX_IMAGE_DIMENSION
                        or width * height > MAX_IMAGE_PIXELS
                    ):
                        raise forms.ValidationError("Les dimensions de l'image sont trop importantes.")
                    image.verify()
            except forms.ValidationError:
                raise
            except (Image.DecompressionBombError, UnidentifiedImageError, OSError, SyntaxError, ValueError) as error:
                raise forms.ValidationError("L'image est invalide ou corrompue.") from error
            finally:
                uploaded_file.seek(0)

        return uploaded_file

    
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
