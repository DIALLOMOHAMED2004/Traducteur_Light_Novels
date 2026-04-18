import cv2
import pytesseract
import os
pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
os.environ['TESSDATA_PREFIX'] = r'C:\\Program Files\\Tesseract-OCR\\tessdata'





def ocr_core(img):
    text = pytesseract.image_to_string(img)
    return text

img = cv2.imread('image1.png')



def grayScale(image):
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def remove_noise(image):
    return cv2.medianBlur(image, 5)


#definition du seuil

def thresholding(image):
    return cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]



#pretraitement

img = grayScale(img)
img = thresholding(img)
img = remove_noise(img)


print(ocr_core(img))

