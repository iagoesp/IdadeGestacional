from __future__ import print_function
import os
import sys
import cv2
import numpy as np
import pydicom
import ctypes
#import matplotlib.pyplot as plt
from PyQt5.QtGui import * 
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
#from functools import partial
#from PIL import Image, ImageQt
from skimage.morphology import disk, binary_erosion

#recebe o tamanho da janela
user32 = ctypes.windll.user32
screensize = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)

# Classe para definir objetos do tipo DICOM e diferenciar
# as suas classes, para facilitar o entendimento

#classe basica Dicom
class Dicom(object):
    def __init__(self, arqDicom):
        self._arquivo = arqDicom
        self._array = None
        self._arrayHQ = None
        self._image = None
        self._imageHQ = None
        self._h = None
    
    def setArquivo(self, arqDicom):
        self._arquivo = arqDicom
    
    def setArray(self, arrayPixel):
        self._array = arrayPixel

    def setImage(self, img):
        self._image = img

    def setArrayHQ(self, arrayPixel):
        self._arrayHQ = arrayPixel

    def setImageHQ(self, img):
        self._imageHQ = img

    def getArquivo(self):
        return self._arquivo
    
    def getArray(self):
        return self._array

    def getImage(self):
        return self._image

    def getArrayHQ(self):
        return self._arrayHQ

    def getImageHQ(self):
        return self._imageHQ

#classe para definir a primeira imagem que sera alinhada 
class DicomOrigin(Dicom):
    def __init__(self, arqDicom):
        super(DicomOrigin, self).__init__(arqDicom)

# Classe principal, que chama a aplicacao
class LabelImage(QWidget):
    global imgOrigin
    global imageReference

    #inicializar variaveis
    def __init__(self):
        super(QWidget, self).__init__()
        self.imageInput = None
        self.initialize = False
        self.isShowed = False
        self.label = QLabel() # Label para exibir a primeira imagem - phatom a ser alinhado
        self.root = QHBoxLayout()
        self.program = QVBoxLayout(self)
        self.initUI()

    #definir itens do layout
    def initUI(self):
        #configurando as labels para exibir as imagens
        self.label.setText('Project: Fetal Ultrasound - V1.0')
        size = QSize(screensize[0]/4, screensize[0]/3)
        #self.label.setMinimumSize(size)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet('border: gray; border-style:solid; border-width: 1px;')
        self.root.addWidget(self.label)
        self.program.addLayout(self.root)

        self.setWindowTitle('Idade Gestacional')
        #self.setWindowFlags(Qt.WindowStaysOnTopHint)
        #self.setWindowFlags(self.windowFlags() & ~Qt.WindowCloseButtonHint)
        #self.setWindowFlags(self.windowFlags() & ~Qt.WindowMinimizeButtonHint)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowMaximizeButtonHint)

    def setText(self, name):
        self.label.setText(name)

    def setGeometryWindow(self):
        self.setWindowTitle('Idade Gestacional - Sem filtro')
        self.setGeometry(00, 110, 300, 200)

    def setGeometryWindow1(self):
        self.setWindowTitle('Idade Gestacional - Com filtro')
        self.setGeometry(600, 110, 300, 200)

    def labelShow(self):
        self.show()

    #redefine o tamanho das imagens
    def processImage(self, thisImage):
        self.imageInput = thisImage

    def setPixmap(self, img):
        try:
            size = img.shape
            step = img.size / size[0]
            qformat = QImage.Format_Indexed8

            if len(size) == 3:
                if size[2] == 4:
                    qformat = QImage.Format_RGBA8888
                else:
                    qformat = QImage.Format_RGB888

            img = QImage(img, size[1], size[0], step, qformat)
            img = img.rgbSwapped()
            self.label.setPixmap(QPixmap.fromImage(img))
        except:
            self.label.setPixmap(img)
    
    def setFixedWidth(self, size):
        self.label.setFixedWidth(size)
    
    def setFixedHeight(self, size):
        self.label.setFixedHeight(size)
               
class IdadeGestacional(QWidget):
    global imgOrigin
    global imageReference

    #inicializar variaveis
    def __init__(self):
        super(QWidget, self).__init__()
        self.setGeometry(0, 30, 20, 20)
        self.imageInput = None
        self.imageUndo = []
        self.imageRedo = []
        self.btn_undo = QPushButton()
        self.btn_redo = QPushButton()
        self.initialize = False
        self.label = LabelImage() # Label para exibir a primeira imagem - phatom a ser alinhado
        self.label1 = LabelImage() # Label para exibir a segunda imagem - phatom de referencia
        self.btn_carregarImagem = QPushButton('Carregar imagem') # Phantom a ser alinhado
        self.btn_refazer = QPushButton('Refazer') # Botao para refazer os alinhamentos e inserir os phantoms
        self.btn_filtro_bilateral = QPushButton('Aplicar filtro bilateral') # Botao para aplicar filtros na imagem alinhada
        self.btn_gaussiano = QPushButton('Aplicar filtro Gaussiano') # Botao para aplicar filtros na imagem alinhada
        self.btn_nitidez = QPushButton('Aplicar filtro de Nitidez') # Botao para aplicar filtros na imagem alinhada
        self.btn_exibirLabels = QPushButton('Exibir imagens') # Botao para alinhar phantoms
        self.top_bar = QHBoxLayout()
        self.program = QVBoxLayout(self)
        self.scroll = QScrollArea()             # Scroll Area which contains the widgets, set as the centralWidget
        self.initUI()

    #definir itens do layout
    def initUI(self):
        self.label.setGeometryWindow()
        self.label1.setGeometryWindow1()
        # chamar as funcoes ao clicar nos botoes, inserir na janela,
        # definir layout e o que deve ser habilitado ou nao
        self.btn_carregarImagem.clicked.connect(self.abrirImagen)
        self.top_bar.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        self.btn_filtro_bilateral.setEnabled(False)
        self.btn_filtro_bilateral.clicked.connect(self.aplicarFBilateral)
        size = QSize(120, 0)
        self.btn_filtro_bilateral.setMinimumSize(size)
        
        self.btn_gaussiano.setEnabled(False)
        self.btn_gaussiano.clicked.connect(self.aplicarFGaussiano)
        size = QSize(screensize[0]/11, 0)
        self.btn_gaussiano.setMinimumSize(size)

        self.btn_nitidez.setEnabled(False)
        self.btn_nitidez.clicked.connect(self.aplicarFNitidez)
        size = QSize(screensize[0]/11, 0)
        self.btn_nitidez.setMinimumSize(size)

        self.btn_exibirLabels.setEnabled(True)
        self.btn_exibirLabels.clicked.connect(self.exibirLabels)
        size = QSize(screensize[0]/11, 0)
        self.btn_exibirLabels.setMinimumSize(size)

        self.btn_refazer.setEnabled(False)
        self.btn_refazer.clicked.connect(self.refazer)

        uIcon = QPixmap('undo20.png')
        self.btn_undo.setIcon(QIcon(uIcon))
        self.btn_undo.clicked.connect(self.goUndo)
        self.btn_undo.setEnabled(False)

        rIcon = QPixmap('redo20.png')
        self.btn_redo.setIcon(QIcon(rIcon))
        self.btn_redo.clicked.connect(self.goRedo)
        self.btn_redo.setEnabled(False)
        
        self.top_bar.addWidget(self.btn_carregarImagem)
        self.top_bar.addWidget(self.btn_filtro_bilateral)
        self.top_bar.addWidget(self.btn_gaussiano)
        self.top_bar.addWidget(self.btn_nitidez)
        self.top_bar.addWidget(self.btn_exibirLabels)
        self.top_bar.addWidget(self.btn_refazer)
        self.top_bar.addWidget(self.btn_undo)
        self.top_bar.addWidget(self.btn_redo)

        self.program.addLayout(self.top_bar)

        #self.showMaximized()
        self.setWindowTitle('Idade Gestacional - Principal')

    def exibirLabels(self):
        self.label.show()
        self.label1.show()

    def goUndo(self):
        if len(self.imageUndo) > 0:
            img = self.imageUndo.pop()
            self.imageInput.setImage(img)
            self.imageRedo.append(img)
            self.label1.setPixmap(img)
            self.btn_redo.setEnabled(True)
        else:
            self.btn_undo.setEnabled(False)
    
    def goRedo(self):
        if len(self.imageRedo) > 0:
            img = self.imageRedo.pop()
            self.imageInput.setImage(img)
            self.imageUndo.append(img)
            self.label1.setPixmap(img)
            self.btn_undo.setEnabled(True)
        else:
            self.btn_redo.setEnabled(False)

    #redefine o tamanho das imagens
    def processImage(self, thisImage):
        height, width = thisImage.getArray().shape
        images = thisImage.getArray()
        height = images.shape[0]
        windowScale = height* 0.002
        newX,newY = images.shape[1]/windowScale, images.shape[0]/windowScale
        images = cv2.resize(images, (int(newX), int(newY)))
        imgOrigin = cv2.convertScaleAbs(images-np.min(images), alpha=(255.0 / min(np.max(images)-np.min(images), 10000)))
        thisImage.setImage(imgOrigin)
        size = thisImage.getImage().shape
        step = thisImage.getImage().size / size[0]
        qformat = QImage.Format_Indexed8

        if len(size) == 3:
            if size[2] == 4:
                qformat = QImage.Format_RGBA8888
            else:
                qformat = QImage.Format_RGB888

        return thisImage.getImage(), size, step, qformat

    #carrega a primeira imagem que sera alinhada
    def abrirImagen(self):
        filename = None
        if self.initialize == False:
            isDCM = False
            filename, _ = QFileDialog.getOpenFileName(None, 'Carregar padrao de phantom', '.', 'DICOM Files (*.dcm);;PNG (*.png)')
            getFilename = os.path.splitext(filename)
            if filename and getFilename[1] =='.dcm':
                isDCM = True
                with open(filename, "rb") as file:
                    self.imageInput = DicomOrigin(pydicom.read_file(file))
                    if self.imageInput == None:
                        print('None')
                    self.imageInput.setArray(self.imageInput.getArquivo().pixel_array)
                    self.imageInput.setImage(self.imageInput.getArquivo().pixel_array)
                    self.imageInput.setImageHQ(self.imageInput.getArquivo().pixel_array)

        img = None
        if isDCM :
            img, size, step, qformat = self.processImage(self.imageInput)
            self.imageInput.setImage(img)
            self.imageUndo.append(img)
            self.label.setPixmap(img)
            self.label1.setPixmap(img)
            img = QImage(self.imageInput.getImage(), size[1], size[0], step, qformat)
            img = img.rgbSwapped()
            self.label.setFixedWidth(size[1])
            self.label.setFixedHeight(size[0])
            self.label1.setFixedWidth(size[1])
            self.label1.setFixedHeight(size[0])

        else:
            pixmap = QPixmap(filename)
            self.label.setPixmap(pixmap)
            self.label1.setPixmap(pixmap)
            self.label.setFixedWidth(pixmap.width())
            self.label.setFixedHeight(pixmap.height())
            self.label1.setFixedWidth(pixmap.width())
            self.label1.setFixedHeight(pixmap.height())
        
        #self.resize(self.label.pixmap().size())
        self.btn_carregarImagem.setEnabled(False)
        self.btn_refazer.setEnabled(True)
        self.btn_filtro_bilateral.setEnabled(True)
        self.btn_gaussiano.setEnabled(True)
        self.btn_nitidez.setEnabled(True)
        self.label.labelShow()
        self.label1.labelShow()

    def aplicarFNitidez(self):
        newImage = self.imageInput.getImage() #retorna imagem com melhor qualidade
        
        # define a matriz para aplicacao do filtro
        kernel_sharpening = np.array([[-1,-1,-1], [-1, 9,-1], [-1,-1,-1]])
        
        newImage = cv2.filter2D(newImage, -1, kernel_sharpening)
        self.imageUndo.append(newImage)
        self.label1.setPixmap(newImage)
        self.imageInput.setImage(newImage)

        size = self.imageInput.getImage().shape
        step = self.imageInput.getImage().size / size[0]
        qformat = QImage.Format_Indexed8

        if len(size) == 3:
            if size[2] == 4:
                qformat = QImage.Format_RGBA8888
            else:
                qformat = QImage.Format_RGB888

        img = QImage(self.imageInput.getImage(), size[1], size[0], step, qformat)
        img = img.rgbSwapped()

        if len(self.imageRedo) > 0 :
            self.imageRedo = []
            self.btn_redo.setEnabled(False)
            
        self.btn_undo.setEnabled(True)

        self.label1.setFixedWidth(size[1])
        self.label1.setFixedHeight(size[0])

    def aplicarFGaussiano(self):
        newImage = self.imageInput.getImage() #retorna imagem com melhor qualidade

        # aplica filtro Gaussiano
        newImage = cv2.GaussianBlur(newImage, (3, 3), 0)

        self.imageUndo.append(newImage)
        self.label1.setPixmap(newImage)
        self.imageInput.setImage(newImage)

        size = self.imageInput.getImage().shape
        step = self.imageInput.getImage().size / size[0]
        qformat = QImage.Format_Indexed8

        if len(size) == 3:
            if size[2] == 4:
                qformat = QImage.Format_RGBA8888
            else:
                qformat = QImage.Format_RGB888

        img = QImage(self.imageInput.getImage(), size[1], size[0], step, qformat)
        img = img.rgbSwapped()

        if len(self.imageRedo) > 0 :
            self.imageRedo = []
            self.btn_redo.setEnabled(False)
            
        self.btn_undo.setEnabled(True)

        self.label1.setFixedWidth(size[1])
        self.label1.setFixedHeight(size[0])

    def aplicarFBilateral(self):
        newImage = self.imageInput.getImage() #retorna imagem com melhor qualidade

        # aplica filtro bilateral
        newImage = cv2.bilateralFilter(newImage,9,75,75)
        self.imageUndo.append(newImage)
        self.label1.setPixmap(newImage)
        self.imageInput.setImage(newImage)
        size = self.imageInput.getImage().shape
        step = self.imageInput.getImage().size / size[0]
        qformat = QImage.Format_Indexed8

        if len(size) == 3:
            if size[2] == 4:
                qformat = QImage.Format_RGBA8888
            else:
                qformat = QImage.Format_RGB888

        img = QImage(self.imageInput.getImage(), size[1], size[0], step, qformat)
        img = img.rgbSwapped() 

        if len(self.imageRedo) > 0 :
            self.imageRedo = []
            self.btn_redo.setEnabled(False)
            
        self.btn_undo.setEnabled(True)

        self.label1.setFixedWidth(size[1])
        self.label1.setFixedHeight(size[0])

    #apaga todas as imagens
    def refazer(self):
        cleanImage = QPixmap()
        self.label.setPixmap(cleanImage)
        self.label.setText('Project: Idade Gestacional - V1.0')

        self.label1.setPixmap(cleanImage)
        self.label1.setText('Project: Idade Gestacional - V1.0')

        self.btn_carregarImagem.setEnabled(True)
        self.btn_refazer.setEnabled(False)
        self.btn_filtro_bilateral.setEnabled(False)
        self.btn_gaussiano.setEnabled(False)
        self.btn_nitidez.setEnabled(False)

        self.btn_undo.setEnabled(False)
        self.btn_redo.setEnabled(False)
        self.imageUndo = []
        self.imageRedo = []

        self.imageInput = None
        self.initialize = False

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = IdadeGestacional()
    win.show()
    sys.exit(app.exec_())