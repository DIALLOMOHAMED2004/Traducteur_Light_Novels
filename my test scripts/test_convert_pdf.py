#MODELE DE TRAITEMENT POUR LES FICHIERS PDF


from pdf2image import convert_from_path
from PIL import Image
import pytesseract
from deep_translator import GoogleTranslator
from docx import Document
from docx2pdf import convert
import os

poppler_path = r'C:/Program Files/poppler-24.08.0/Library\bin'
os.environ["PATH"] += os.pathsep + poppler_path

pytesseract.pytesseract.tesseract_cmd = r"C:/Program Files/Tesseract-OCR/tesseract.exe"

config = '--oem 3 --psm 6'


#chemin vers le fichier PDF
pdf_path = 'Medias_test/test3.pdf'


#convertion des pages du pdf en images
pages = convert_from_path(pdf_path, dpi=300, output_folder='Medias_test', poppler_path=poppler_path)

#extraire le texte de chaque page

for i, page in enumerate(pages):
    text = pytesseract.image_to_string(page, lang='eng', config=config)
    print(f"----page {i+1}----")

    #traduction des pages convertis en image en francais
    #code pour traduire en francais le text extrait
    #translated_fr = GoogleTranslator(source='en', target='fr').translate(text)

    #code pour recuperer le text traduit et l'inserer dans un fichier docx
    doc = Document()
    doc.add_heading('TRADUIT PAR ZENIA')
    doc.add_paragraph(text)
    #doc.add_picture('Medias_test\page 1.PNG')
    doc.save(f'Media_convert_docx/trad{i}.docx')


#code qui fusionne tous les fichiers docx separé en un seul
folder_doc  = 'Media_convert_docx'
merged_doc = Document()
for filename in os.listdir(folder_doc):
    if filename.endswith('.docx'):
        docu = Document(os.path.join(folder_doc, filename))
        for element in docu.element.body:
            merged_doc.element.body.append(element)
        #merged_doc.add_page_break()
        
merged_doc.save('Media_fusionné/document_fusionné1.docx')

#code qui permet de convertir le fichier docx en pdf
convert('Media_fusionné/document_fusionné1.docx', "Media_fusionné/document_fusionné.pdf")

#suppression des fichier .ppm du repertoire source

folder_ppm = 'Medias_test'

for file_drop in os.listdir(folder_ppm):
    if file_drop.endswith('.ppm'):
        path_file = os.path.join(folder_ppm, file_drop)
        os.remove(path_file)


#suppression des fichier docx separé

folder_docx_separated = 'Media_convert_docx'

for file_drop_docx in os.listdir(folder_docx_separated):
    if file_drop_docx.endswith('.docx'):
        path_file_docx = os.path.join(folder_docx_separated, file_drop_docx)
        os.remove(path_file_docx)










