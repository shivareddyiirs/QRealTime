# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QRealTimeDialog
                                 A QGIS plugin
 This plugin connects you to KoBoToolbox Server
                             -------------------
        begin                : 2019-01-13
        git sha              : $Format:%H$
        copyright            : (C) 2019 by IIRS
        email                : kotishiva@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import os
from PyQt5 import QtGui, uic
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QTableWidget,QTableWidgetItem
from PyQt5.QtCore import Qt, QSettings, QSize,QVariant
import xml.etree.ElementTree as ET
import requests
from qgis.gui import QgsMessageBar
from qgis.core import QgsProject,QgsFeature,QgsGeometry,QgsField, QgsCoordinateReferenceSystem, QgsPoint, QgsCoordinateTransform,edit,QgsPointXY,QgsEditorWidgetSetup
import six
from six.moves import range
from qgis.core import QgsMessageLog, Qgis
import csv
import codecs
tag='KoBoToolbox'
def print(text,opt=None):
    """ to redirect print to MessageLog"""
    QgsMessageLog.logMessage(str(text)+str(opt),tag=tag,level=Qgis.Info)
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'QRealTime_dialog_services.ui'))

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
class QRealTimeDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, caller,parent=None):
        """Constructor."""
        super(QRealTimeDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        service='KoBoToolbox'
        container = self.tabServices.widget(0)
        serviceClass = globals()[service]
        serviceClass(container,caller)
        self.tabServices.setTabText(0, service)
    
    def getCurrentService(self):
        return self.tabServices.currentWidget().children()[0]

class KoBoToolbox (QTableWidget):
    parameters = [
        ["id","KoBoToolbox"],
        ["user", ''],
        ["password", ''],
        ["lastID",''],
        ['sync time','']
        ]
    kpi='https://kf.kobotoolbox.org/'
    def __init__(self,parent,caller):
        super(KoBoToolbox, self).__init__(parent)
        self.parent = parent
        self.iface=caller.iface
        self.resize(QSize(310,260))
        self.setColumnCount(2)
        self.setColumnWidth(0, 152)
        self.setColumnWidth(1, 152)
        self.setRowCount(len(self.parameters)-1)
        self.verticalHeader().hide()
        self.horizontalHeader().hide()
        self.token=''
        
        S = QSettings()
        for row,parameter in enumerate(self.parameters):
            if row == 0:
                self.service_id = parameter[1]
                continue
            row = row -1
            pKey = QTableWidgetItem (parameter[0])
            pKey.setFlags(pKey.flags() ^ Qt.ItemIsEditable)
            pValue = QTableWidgetItem (parameter[1])
            self.setItem(row,0,pKey)
            valueFromSettings = S.value("KoBoToolbox/%s/%s/" % (self.service_id,self.item(row,0).text()), defaultValue =  "undef")
            if not valueFromSettings or valueFromSettings == "undef":
                self.setItem(row,1,pValue)
                S.setValue("KoBoToolbox/%s/%s/" % (self.service_id,self.item(row,0).text()),parameter[1])
            else:
                self.setItem(row,1,QTableWidgetItem (valueFromSettings))


    def getServiceName(self):
        return self.service_id
     
    def getAuth(self):
        url= self.kpi+'token'
        para={'format':'json'}
        response = requests.get(url,auth=(self.getValue('user'), self.getValue('password')),params=para)
        token=response.json()['token']
        headers = {
    'Authorization': 'Token '+ token,
}
        return headers

    def setup(self):
        S = QSettings()
        S.setValue("KoBoToolbox/", self.parent.parent().currentIndex())
        for row in range (0,self.rowCount()):
            S.setValue("KoBoToolbox/%s/%s/" % (self.service_id,self.item(row,0).text()),self.item(row,1).text())
        
    def getValue(self,key, newValue = None):
        for row in range (0,self.rowCount()):
            if self.item(row,0).text() == key:
                if newValue:
                    self.item(row, 1).setText(newValue)
                    self.setup() #store to settings
                return self.item(row,1).text()
        raise AttributeError("key not found: " + key)

    def guessGeomType(self,geom):
        coordinates = geom.split(';')
        firstCoordinate = coordinates[0].strip().split(' ')
        coordinatesList = []
        if len(firstCoordinate) < 2:
            return "invalid", None
        for coordinate in coordinates:
            decodeCoord = coordinate.strip().split(' ')
            coordinatesList.append([decodeCoord[0],decodeCoord[1]])
        if len(coordinates) == 1:
            return "Point", coordinatesList #geopoint
        if coordinates[-1] == '' and coordinatesList[0][0] == coordinatesList[-2][0] and coordinatesList[0][1] == coordinatesList[-2][1]:
            return "Polygon", coordinatesList #geoshape #geotrace
        else:
            return "LineString", coordinatesList


   

#    def getExportExtension(self):
#        return 'xml'
        
    def getFormList(self):
        user=self.getValue('user')
        url=self.kpi+'assets/'
        print (url)
        status='not able to download'
        para={'format':'json'}
        response= requests.get(url,headers=self.getAuth(),params=para)
        forms= response.json()
        try:
            keyDict= {form['uid']:form['name'] for form in forms['results']}
            print('keyDict is',keyDict)
            return keyDict,response
        except:
            print ('getformList','not able to get the forms')
            return {},response
    
            
    def sendForm(self,xForm_id,xForm):
        
#        step1 - verify if form exists:
        formList, response = self.getFormList()
        form_key=xForm_id in formList
        if response.status_code != requests.codes.ok:
            print(status)
            return status
        message =''
        if form_key:
            message= 'Form Updated'
            method = 'POST'
            url = kpi+'/api/v1/forms'
        else:
            message= 'Created new form'
            method = 'POST'
            url = kpi+'/api/v1/forms'
        os.chdir(os.path.expanduser('~'))
        files = {'xls_file': (xForm, open(xForm, 'rb')),}
        response = requests.post(url,files=files,headers=self.getAuth())
        if response.status_code== 201 or response.status_code == 200:
            self.iface.messageBar().pushSuccess(self.tr("KoBoToolbox plugin"),
                                                self.tr('Layer is online('+message+'), Collect data from App'))
        elif response.status_code == 409:
            self.iface.messageBar().pushWarning(self.tr("KoBoToolbox plugin"),self.tr("Form exist and can not be updated"))
        else:
            self.iface.messageBar().pushCritical(self.tr("KoBoToolbox plugin"),self.tr(str(response.status_code)))
        return response
        
    def collectData(self,layer,xFormKey,importData=False,topElement='',version='null',geoField=''):
#        if layer :
#            print("layer is not present or not valid")
#            return
        self.updateFields(layer)
        if importData:
            response,remoteTable = self.getTable(xFormKey,"",topElement,version)
        else:
            response,remoteTable = self.getTable(xFormKey,self.getValue('lastID'),topElement,version)
        print ('before Update Layer')
        if response.status_code==200:
            if remoteTable:
                print ('table have some data')
                self.updateLayer(layer,remoteTable,geoField)
        else:
            self.iface.messageBar().pushCritical(self.tr("KoBoToolbox"),self.tr("Not able to collect data from KoBoToolbox"))
    
    def updateFields(self,layer,text='instanceID',q_type=QVariant.String,config={}):
        flag=True
        for field in layer.fields():
            
            if field.name()[:10] == text[:10]:
                flag=False
                print("not writing fields")
        if flag:
            uuidField = QgsField(text, q_type)
            if q_type == QVariant.String:
                uuidField.setLength(100)
            layer.dataProvider().addAttributes([uuidField])
            layer.updateFields()
        fId= layer.dataProvider().fieldNameIndex(text)
        try:
            if config['type']== 'Hidden':
                print('setting hidden widget')
                layer.setEditorWidgetSetup( fId, QgsEditorWidgetSetup( "Hidden" ,config ) )
                return
        except:
            print('exception')
        if config=={}:
            return
        print('now setting exernal resource widgt')
        layer.setEditorWidgetSetup( fId, QgsEditorWidgetSetup( "ExternalResource" ,config ) )
    def updateLayer(self,layer,dataDict,geoField):
        #print "UPDATING N.",len(dataDict),'FEATURES'
        self.processingLayer = layer
        QgisFieldsList = [field.name() for field in layer.fields()]
        #layer.beginEditCommand("ODK syncronize")
#        layer.startEditing()
        type=layer.geometryType()
        geo=['POINT','LINE','POLYGON']
        layerGeo=geo[type]
        
        uuidList = self.getUUIDList(self.processingLayer)

        newQgisFeatures = []
        fieldError = None
        for odkFeature in dataDict:
            try:
                qgisFeature = QgsFeature()
                odkFeature=dict(odkFeature)
                print('dict is',odkFeature)
                wktGeom = self.guessWKTGeomType(odkFeature[geoField])
                print (wktGeom)
                if wktGeom[:3] != layerGeo[:3]:
                    continue
                qgisGeom = QgsGeometry.fromWkt(wktGeom)
                print('geom is',qgisGeom)
                qgisFeature.setGeometry(qgisGeom)
                qgisFeature.initAttributes(len(QgisFieldsList))
                for fieldName, fieldValue in six.iteritems(odkFeature):
                    try:
                        qgisFeature.setAttribute(QgisFieldsList.index(fieldName),fieldValue)
                    except:
                        fieldError = fieldName
                                
                newQgisFeatures.append(qgisFeature)
                        
            except Exception as e :
                print(e)
                
                
        if fieldError:
            self.iface.messageBar().pushWarning(self.tr("KoBoToolbox"), self.tr("Can't find '%s' field") % fieldError)
        
        with edit(layer):
            layer.addFeatures(newQgisFeatures)
        self.processingLayer = None
        
    def getUUIDList(self,lyr):
        uuidList = []
        if lyr:
            for qgisFeature in lyr.getFeatures():
                uuidList.append(qgisFeature['instanceID'])
        return uuidList

    def guessWKTGeomType(self,geom):
        if geom:
            coordinates = geom.split(';')
        else:
            return 'error'
#        print ('coordinates are '+ coordinates)
        firstCoordinate = coordinates[0].strip().split(" ")
        if len(firstCoordinate) < 2:
            return "invalid", None
        coordinatesList = []
        for coordinate in coordinates:
            decodeCoord = coordinate.strip().split(" ")
#            print 'decordedCoord is'+ decodeCoord
            try:
                coordinatesList.append([decodeCoord[0],decodeCoord[1]])
            except:
                pass
        if len(coordinates) == 1:
            
            reprojectedPoint = self.transformToLayerSRS(QgsPoint(float(coordinatesList[0][1]),float(coordinatesList[0][0])))
            return "POINT(%s %s)" % (reprojectedPoint.x(), reprojectedPoint.y()) #geopoint
        else:
            coordinateString = ""
            for coordinate in coordinatesList:
                reprojectedPoint = self.transformToLayerSRS(QgsPoint(float(coordinate[1]), float(coordinate[0])))
                coordinateString += "%s %s," % (reprojectedPoint.x(), reprojectedPoint.y())
            coordinateString = coordinateString[:-1]
        if  coordinatesList[0][0] == coordinatesList[-1][0] and coordinatesList[0][1] == coordinatesList[-1][1]:
            return "POLYGON((%s))" % coordinateString #geoshape #geotrace
        else:
            return "LINESTRING(%s)" % coordinateString
            
    def transformToLayerSRS(self, pPoint):
        # transformation from the current SRS to WGS84
        crsDest = self.processingLayer.crs () # get layer crs
        crsSrc = QgsCoordinateReferenceSystem(4326)  # WGS 84
        xform = QgsCoordinateTransform(crsSrc, crsDest, QgsProject.instance())
        try:
            return QgsPoint(xform.transform(pPoint))
        except :
            return QgsPoint(xform.transform(QgsPointXY(pPoint)))


        
                                                
    def getTable(self,XFormKey,lastID,topElement,version= 'null'):
        url='https://kc.kobotoolbox.org/'+self.getValue('user')+'/reports/'+XFormKey+'/export.csv'
        method='GET'
        print('inside getTable',url)
        table=[]
        response = requests.request(method,url,proxies=getProxiesConf(),headers=self.getAuth(),verify=False)
        if not response.status_code == 200:
                return response, table
        try:
            print('response content  is',response.text)
            data = csv.DictReader(response.text.splitlines(),delimiter=';')
            print('dictionary is',data)
            table=data
            print ('table is:',table)
            return response, table
        except Exception as e:
            print ('not able to fetch',e)
            return response, table
