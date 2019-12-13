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
from qgis.core import QgsMessageLog, Qgis
tag='QRealTime'
def print(text,opt=''):
    """ to redirect print to MessageLog"""
    QgsMessageLog.logMessage(str(text)+str(opt),tag=tag,level=Qgis.Info)
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
        self.menu = 'QRealTime'
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar('QRealTime')
        self.toolbar.setObjectName('QRealTime')

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
    
    def add_layer_action( self,icon_path,text,callback,icon_enabled=True,add_to_vLayer=True,enabled_flag=True,parent=None):
        icon = QIcon(icon_path)
        if icon_enabled:
            action = QAction(icon, text,parent)
        else:
            action = QAction(text,parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)
        if add_to_vLayer:
            self.iface.addCustomActionForLayerType(action,'QRealTime',
                                                   QgsMapLayer.VectorLayer,True)
        self.actions.append(action)

        return action
    
    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = os.path.join(self.plugin_dir,'icon.png')
        self.add_action(icon_path,text=self.tr(u'QRealTime Setting'),callback=self.run,parent=self.iface.mainWindow())
        """add sync action"""
        self.sync= self.add_layer_action(icon_path,self.tr(u'sync'),self.download,False)
	# make sync action checkable and default to unchecked
        self.sync.setCheckable(True)
        self.sync.setChecked(False)
        """add import action """
        self.Import=self.add_layer_action(icon_path,self.tr(u'import'),self.importData)
        """add makeonline action """
        self.makeOnline=self.add_layer_action(icon_path,self.tr(u'Make Online'),self.sendForm)
        service=self.dlg.getCurrentService()
        self.service=service
        self.topElement= None
        self.version=''
        try:
            self.time=3600
            self.time=int(service.getValue(self.tr('sync time')))
        except:
            print ('can not read time')
        self.timer=QTimer()
        def timeEvent():
            print ('calling collect data')
            self.service.importData(self.layer,self.formID,False)
        self.timer.timeout.connect(timeEvent)


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                'QRealTime',
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
        if response:
	        if response.status_code==200:
	            self.ImportData=ImportData()
	            for name,key in forms.items():
	            	self.ImportData.comboBox.addItem(name,key)
	            self.ImportData.show()
	            result=self.ImportData.exec_()
	            if result:
	                selectedForm= self.ImportData.comboBox.currentData()
	                service.importData(layer,selectedForm,True)            
    def getLayer(self):
        return self.iface.activeLayer()
        
    def sendForm(self):
#        get the fields model like name , widget type, options etc.
        layer=self.getLayer()
        service=self.dlg.getCurrentService()
        service.prepareSendForm(layer)
        
    def download(self,checked=False):
        if checked==True:
            self.layer= self.getLayer()
            self.service=self.dlg.getCurrentService()
            forms,response= self.service.getFormList()
            if response:
                self.formID= forms[self.layer.name()]
                print('starting timer every'+ str(self.time)+'second')
                self.timer.start(1000*self.time)
        elif checked==False:
            self.timer.stop()
            
    
