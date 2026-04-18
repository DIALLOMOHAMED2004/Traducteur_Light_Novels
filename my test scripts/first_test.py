from PyPDF2 import PdfReader

reader = PdfReader('media\\t.pdf')

#obtenir le nombre de page

nbr_page = len(reader.pages)

print(f"le fichier contient : {nbr_page} pages")