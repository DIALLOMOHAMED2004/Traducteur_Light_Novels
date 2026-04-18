#MODELE DE TRAITEMENT POUR LES FICHIERS PDF







from docx2pdf import convert
import os
import random


folder = 'media_upload/templates CV'

for element in os.listdir(folder):
    
    if element.endswith('.docx'):
        path_doc = os.path.join(folder, element)
        convert(path_doc, f'{folder}/{random.random()}.pdf')
        #print(element)



  















