from PyQt5 import QtGui,QtWidgets, uic
import os
from qgis.core import *


FORM_CLASS, _ = uic.loadUiType(os.path.join( os.path.dirname(__file__), 'QRealTime_dialog_import.ui'))

    
class importData(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self,parent=None):
        super(importData,self).__init__(parent)
        self.setupUi(self)
        
