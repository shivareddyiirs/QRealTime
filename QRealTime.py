# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QRealTime
                                 A QGIS plugin
 This plugin connects you to Aggregate Server and do autoupdation of data to and from aggregate
                              -------------------
        begin                : 2017-08-09
        git sha              : $Format:%H$
        copyright            : (C) 2017 by IIRS
        email                : kotishiva@gmail.com
 ***************************************************************************/
  code is taken and modified from:
        copyright            : (C) 2016 by Enrico Ferreguti
        email                : enricofer@gmail.com
/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt5.QtCore import QSettings, QTranslator, qVersion, QCoreApplication,QVariant
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QMenu,QAction, QFileDialog
# import for XML reading writing
# Import the code for the dialog
from .QRealTime_dialog import QRealTimeDialog
from .QRealTime_dialog_import import ImportData
import os.path
from qgis.core import QgsMapLayer
import warnings
import unicodedata
import re
import json
from qgis.PyQt.QtCore import QTimer
import requests
import xml.etree.ElementTree as ET
import subprocess
from qgis.core import QgsMessageLog, Qgis
tag='QRealTime'
def print(text,opt=''):
    """ to redirect print to MessageLog"""
    QgsMessageLog.logMessage(str(text)+str(opt),tag=tag,level=Qgis.Info)
import six

def getProxiesConf():
    s = QSettings() #getting proxy from qgis options settings
    proxyEnabled = s.value("proxy/proxyEnabled", "")
    proxyType = s.value("proxy/proxyType", "" )
    proxyHost = s.value("proxy/proxyHost", "" )
    proxyPort = s.value("proxy/proxyPort", "" )
    proxyUser = s.value("proxy/proxyUser", "" )
    proxyPassword = s.value("proxy/proxyPassword", "" )
    if proxyEnabled == "true" and proxyType == 'HttpProxy': # test if there are proxy settings
        proxyDict = {
            "http"  : "http://%s:%s@%s:%s" % (proxyUser,proxyPassword,proxyHost,proxyPort),
            "https" : "http://%s:%s@%s:%s" % (proxyUser,proxyPassword,proxyHost,proxyPort) 
        }
        return proxyDict
    else:
        return None

    
class QRealTime:
    """QGIS Plugin Implementation."""


    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale//userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'QRealTime_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)


        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&QRealTime')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'QRealTime')
        self.toolbar.setObjectName(u'QRealTime')

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('QRealTime', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        # Create the dialog (after translation) and keep reference
        self.dlg = QRealTimeDialog(self)

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = os.path.join(self.plugin_dir,'icon.png')
        self.add_action(
            icon_path,
            text=self.tr(u'QRealTime Setting'),
            callback=self.run,
            parent=self.iface.mainWindow())
        self.ODKMenu = QMenu('QRealTime')
        icon = QIcon(icon_path)
        self.sync= QAction(self.tr(u'sync'),self.ODKMenu)
        self.sync.setCheckable(True)
        self.sync.setChecked(False)
        self.sync.triggered.connect(self.download)
        self.sync.setChecked(False)
        self.iface.addCustomActionForLayerType(
                self.sync,
                'QRealTime',
                QgsMapLayer.VectorLayer,
                True)

        self.Import = QAction(icon,self.tr(u'import'),self.ODKMenu)
        self.Import.triggered.connect(self.importData)
        self.iface.addCustomActionForLayerType(
                self.Import,
                'QRealTime',
                QgsMapLayer.VectorLayer,
                True)
        self.makeOnline=QAction(icon,self.tr(u'Make Online'),self.ODKMenu)
        self.makeOnline.triggered.connect(self.sendForm)
        self.iface.addCustomActionForLayerType(
            self.makeOnline,
            'QRealTime',
            QgsMapLayer.VectorLayer,
            True)
        service=self.dlg.getCurrentService()
        self.service=service
        self.topElement= None
        self.version=''
        try:
            self.time=1
            self.time=int(service.getValue('sync time'))
        except:
            print ('can not read time')
        self.timer=QTimer()
        def timeEvent():
            print ('calling collect data')
            layer=self.getLayer()
            print(layer)
            if (not self.topElement):
                url=service.getValue('url')+'//formXml?formId='+layer.name()
                response= requests.request('GET',url,proxies=getProxiesConf(),auth=service.getAuth(),verify=False)
                if response.status_code==200:
                    self.formKey,self.topElement,self.version,self.geoField = service.updateLayerXML(layer,response.content)
            service.collectData(layer,layer.name(),False,self.topElement,self.version,self.geoField)
        self.timer.timeout.connect(timeEvent)


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'QRealTime'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        self.iface.removeCustomActionForLayerType(self.sync)
        self.iface.removeCustomActionForLayerType(self.makeOnline)
        self.iface.removeCustomActionForLayerType(self.Import)
        del self.toolbar


    def run(self):
        """Run method that performs all the real work"""
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            self.dlg.getCurrentService().setup()
            
    def importData(self):
        service=self.dlg.getCurrentService()
        layer=self.getLayer()
        forms,response= service.getFormList()
        if response.status_code==200:
            self.ImportData=ImportData()
            self.ImportData.comboBox.addItems(forms)
            self.ImportData.show()
            result=self.ImportData.exec_()
            if result:
                selectedForm= self.ImportData.comboBox.currentText()
                service.importData(layer,selectedForm)            
    def getLayer(self):
        return self.iface.activeLayer()
        
    def sendForm(self):
#        get the fields model like name , widget type, options etc.
        layer=self.getLayer()
        service=self.dlg.getCurrentService()
        service.updateFields(layer)
        service.prepareForm(layer,'Xform.xml') 
        service.sendForm(layer.name(),'Xform.xml')
    def download(self,checked=False):
        if checked==True:
            self.layer= self.getLayer()
            self.time=int(self.service.getValue('sync time'))
            print('starting timer every'+ str(self.time)+'second')
            self.timer.start(1000*self.time)
        elif checked==False:
            self.timer.stop()
            
    
