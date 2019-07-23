# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QRealTime-KoBo
                                 A QGIS plugin
 This plugin connects you to KoBoToolbox
                              -------------------
        begin                : 2019-01-13
        git sha              : $Format:%H$
        copyright            : (C) 2019 by IIRS
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
from .QRealTimeKoBo_dialog import QRealTimeKoBoDialog
from .QRealTimeKoBo_dialog_import import ImportData
import os.path
from qgis.core import QgsMapLayer
import warnings
import re
import json
from qgis.PyQt.QtCore import QTimer
import datetime
import requests
import xml.etree.ElementTree as ET
from qgis.core import QgsMessageLog, Qgis

tag='QRealTime-KoBo'
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
    
def QVariantToODKtype(q_type):
        if  q_type == QVariant.String:
            return 'text'
        elif q_type == QVariant.Date:
            return 'datetime'
        elif q_type in [2,3,4,32,33,35,36]:
            return 'integer'
        elif q_type in [6,38]:
            return 'decimal'
        else:
            raise AttributeError("Can't cast QVariant to ODKType: " + q_type)

def qtype(odktype):
    if odktype == 'binary':
        return QVariant.String,{'DocumentViewer': 2, 'DocumentViewerHeight': 0, 'DocumentViewerWidth': 0, 'FileWidget': True, 'FileWidgetButton': True, 'FileWidgetFilter': '', 'PropertyCollection': {'name': None, 'properties': {}, 'type': 'collection'}, 'RelativeStorage': 0, 'StorageMode': 0}
    elif odktype=='string':
        return QVariant.String,{}
    elif odktype[:3] == 'sel' :
        return QVariant.String,{}
    elif odktype[:3] == 'int':
        return QVariant.Int, {}
    elif odktype[:3]=='dat':
        return QVariant.Date, {}
    elif odktype[:3]=='ima':
        return QVariant.String,{'DocumentViewer': 2, 'DocumentViewerHeight': 0, 'DocumentViewerWidth': 0, 'FileWidget': True, 'FileWidgetButton': True, 'FileWidgetFilter': '', 'PropertyCollection': {'name': None, 'properties': {}, 'type': 'collection'}, 'RelativeStorage': 0, 'StorageMode': 0}
    elif odktype == 'Hidden':
        return 'Hidden'
    else:
        return (QVariant.String),{}
    
class QRealTimeKoBo:
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
            'QRealTime-KoBo_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)


        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&QRealTime-KoBo')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'QRealTime-KoBo')
        self.toolbar.setObjectName(u'QRealTime-KoBo')

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
        return QCoreApplication.translate('QRealTime-KoBo', message)


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
        self.dlg = QRealTimeKoBoDialog(self)

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
            text=self.tr(u'QRealTime-KoBo Settings'),
            callback=self.run,
            parent=self.iface.mainWindow())
        self.ODKMenu = QMenu('QRealTime-KoBo')
        icon = QIcon(icon_path)
        self.sync= QAction(self.tr(u'sync'),self.ODKMenu)
        self.sync.setCheckable(True)
        self.sync.setChecked(False)
        self.sync.triggered.connect(self.download)
        self.sync.setChecked(False)
        self.iface.addCustomActionForLayerType(
                self.sync,
                'QRealTime-KoBo',
                QgsMapLayer.VectorLayer,
                True)

        self.Import = QAction(icon,self.tr(u'Import'),self.ODKMenu)
        self.Import.triggered.connect(self.importData)
        self.iface.addCustomActionForLayerType(
                self.Import,
                'QRealTime-KoBo',
                QgsMapLayer.VectorLayer,
                True)
        self.makeOnline=QAction(icon,self.tr(u'Deploy Form'),self.ODKMenu)
        self.makeOnline.triggered.connect(self.sendForm)
        self.iface.addCustomActionForLayerType(
            self.makeOnline,
            'QRealTime-KoBo',
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
            layer=self.getLayer()
            service=self.dlg.getCurrentService()
            print(layer)
            if (not self.topElement):
                self.topElement= layer.name()
                url='https://kc.humanitarianresponse.info/api/v1/data'
                response = requests.get(url,auth=(service.getValue('user'),service.getValue('password')),verify=False)
                responseJSON=json.loads(response.text)
                formUID=''
                for form in responseJSON:
                    if str(form['title'])==self.topElement:
                        formUID=form['id_string']
                xmlurl="https://kobo.humanitarianresponse.info/assets/"+formUID
                para={'format':'xml'}
                response=requests.get(xmlurl,auth=(service.getValue('user'),service.getValue('password')),params=para)
                self.formKey,self.version,self.geoField,self.fields = self.updateLayer(layer,response.content)
            service.collectData(layer,formUID,self.fields,self.geoField,False,self.topElement,self.version)
        self.timer.timeout.connect(timeEvent)


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'QRealTime-KoBo'),
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
            for key,name in forms.items():
                self.ImportData.comboBox.addItem(name,key)
            self.ImportData.show()
            result=self.ImportData.exec_()
            if result:
                index=self.ImportData.comboBox.currentIndex()
                selectedForm= self.ImportData.comboBox.itemData(index)
                url='https://kobo.humanitarianresponse.info/assets/'+selectedForm
                para={'format':'xml'}
                #headers=service.getAuth()
                requests.packages.urllib3.disable_warnings()
                response= requests.request('GET',url,proxies=getProxiesConf(),auth=(service.getValue('user'), service.getValue('password')),verify=False,params=para)
                if response.status_code==200:
                    xml=response.content
                    # with open('importForm.xml','w') as importForm:
                    #     importForm.write(response.content)
                    self.layer_name,self.version, self.geoField,self.fields= self.updateLayer(layer,xml)
                    layer.setName(self.layer_name)
                    service.collectData(layer,selectedForm,self.fields,self.geoField,True,self.layer_name,self.version)

                
                        
    def updateLayer(self,layer,xml):
        geoField=''
        ns='{http://www.w3.org/2002/xforms}'
        nsh='{http://www.w3.org/1999/xhtml}'
        root= ET.fromstring(xml)
        #key= root[0][1][0][0].attrib['id']
        layer_name=root[0].find(nsh+'title').text
        instance=root[0][1].find(ns+'instance')
        fields={}
        #topElement=root[0][1][0][0].tag.split('}')[1]
        try:
            version=instance[0].attrib['version']
        except:
            version='null'
#        print('form name is '+ layer_name)
#        print (root[0][1].findall(ns+'bind'))
        for bind in root[0][1].findall(ns+'bind'):
            attrib=bind.attrib
            print (attrib)
            fieldName= attrib['nodeset'].split('/')[-1].replace("_", " ")
            fieldType=attrib['type']
            fields[fieldName]=fieldType
#            print('attrib type is',attrib['type'])
            qgstype,config = qtype(attrib['type'])
#            print ('first attribute'+ fieldName)
            inputs=root[1].findall('.//*[@ref]')
            if fieldType[:3]!='geo':
                #print('creating new field:'+ fieldName)
                isHidden= True
                for input in inputs:
                    if fieldName == input.attrib['ref'].split('/')[-1].replace("_", " "):
                        isHidden= False
                        break
                if isHidden:
                    print('Reached Hidden')
                    config['type']='Hidden'
                self.dlg.getCurrentService().updateFields(layer,fieldName,qgstype,config)
            else:
                geoField=fieldName
                self.dlg.getCurrentService().updateFields(layer,fieldName,qgstype,config)
                print('geometry field is =',fieldName)
        return layer_name,version,geoField,fields


    def getLayer(self):
        return self.iface.activeLayer()
        
    def sendForm(self):
#        get the fields model like name , widget type, options etc.
        layer=self.getLayer()
        self.dlg.getCurrentService().updateFields(layer)
        fieldDict,choicesList= self.getFieldsModel(layer)
        print ('fieldDict',fieldDict)
        payload={"name":layer.name(),"asset_type":"survey","content":json.dumps({"survey":fieldDict,"choices":choicesList})}
        print("Payload= ",payload)
        self.dlg.getCurrentService().sendForm('',layer.name(),payload)

    def download(self,checked=False):
        if checked==True:
            self.layer= self.getLayer()
            self.time=int(self.service.getValue('sync time'))
            print('starting timer every'+ str(self.time)+'second')
            self.timer.start(1000*self.time)
        elif checked==False:
            self.timer.stop()
            
    def getFieldsModel(self,currentLayer):
        fieldsModel = []
        choicesList = []
        g_type= currentLayer.geometryType()
        fieldDef={"type":"geopoint","required":True}
#        fieldDef['Appearance']= 'maps'
        if g_type==0:
            fieldDef["label"]="Point Location"
        elif g_type==1:
            fieldDef["label"]="Draw Line"
            fieldDef["type"]="geotrace"
        else:
            fieldDef["label"]="Draw Area"
            fieldDef["type"]="geoshape"
        fieldsModel.append(fieldDef)
        i=0
        j=0
        for field in currentLayer.fields():
            widget =currentLayer.editorWidgetSetup(i)
            fwidget = widget.type()
            if (fwidget=='Hidden'):
                i+=1
                continue
                
            fieldDef = {}
            fieldDef["label"] = field.alias() or field.name()
#            fieldDef['hint'] = ''
            fieldDef["type"] = QVariantToODKtype(field.type())
#            fieldDef['bind'] = {}
#            fieldDef['fieldWidget'] = currentFormConfig.widgetType(i)
            fieldDef["fieldWidget"]=widget.type()
            print("getFieldModel",fieldDef["fieldWidget"])
            if fieldDef["fieldWidget"] in ("ValueMap","CheckBox","Photo","ExternalResource"):
                if fieldDef["fieldWidget"] == "ValueMap":
                    fieldDef["type"]="select_one"
                    j+=1
                    listName="select"+str(j)
                    fieldDef["select_from_list_name"]=listName
                    valueMap=widget.config()["map"]
                    config={}
                    for value in valueMap:
                        for k,v in value.items():
                                config[v]=k
                    print('configuration is ',config)
                    for name,label in config.items():
                        choicesList.append({"name":name,"label":label,"list_name":listName})
#                    fieldDef["choices"] = choicesList
                elif fieldDef["fieldWidget"] == 'Photo' or fieldDef["fieldWidget"] == 'ExternalResource' :
                    fieldDef["type"]="image"
                    print('got an image type field')
                
#                fieldDef['choices'] = config
#            else:
#                fieldDef['choices'] = {}
#            if fieldDef['name'] == 'ODKUUID':
#                fieldDef["bind"] = {"readonly": "true()", "calculate": "concat('uuid:', uuid())"}
            fieldDef.pop("fieldWidget")
            for key, value in list(fieldDef.items()):
                if value[:8]=="instance":
                    fieldDef.pop(key)
                    fieldDef.pop("type")
            fieldsModel.append(fieldDef)
            i+=1
        return fieldsModel,choicesList
