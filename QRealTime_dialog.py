# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QRealTimeDialog
                                 A QGIS plugin
 This plugin connects you to Aggregate Server and do autoupdation of data to and from aggregate
                             -------------------
        begin                : 2017-08-09
        git sha              : $Format:%H$
        copyright            : (C) 2017 by IIRS
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
tag='ODK-Central'
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
        service='aggregate'
        container = self.tabServices.widget(0)
        serviceClass = globals()[service]
        serviceClass(container,caller)
        self.tabServices.setTabText(0, service)
    
    def getCurrentService(self):
        return self.tabServices.currentWidget().children()[0]

class aggregate (QTableWidget):
    parameters = [
        ["id","aggregate"],
        ["url",''],
        ["user", ''],
        ["password", ''],
        ["lastID",''],
        ['sync time','']
        ]
        
    def __init__(self,parent,caller):
        super(aggregate, self).__init__(parent)
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
            valueFromSettings = S.value("QRealTime/%s/%s/" % (self.service_id,self.item(row,0).text()), defaultValue =  "undef")
            if not valueFromSettings or valueFromSettings == "undef":
                self.setItem(row,1,pValue)
                S.setValue("QRealTime/%s/%s/" % (self.service_id,self.item(row,0).text()),parameter[1])
            else:
                self.setItem(row,1,QTableWidgetItem (valueFromSettings))


    def getServiceName(self):
        return self.service_id
     
    def getAuth(self):
        url=self.getValue('url')+'/v1'+'/sessions'
        print('session url is test', url)
        value= """
  {
    "email": "kotishiva@gmail.com",
    "password": "Shivram@9"
  }
"""
        print('payload is',value)
        headers={'Content-Type': 'application/json'}
        response = requests.post(url,data=value, headers=headers)
        session=response.json()
        self.token= session['token']
        print('Printing token',self.token)
        tokenHeader = {'Authorization': 'Bearer '+ self.token}
        return tokenHeader

    def setup(self):
        S = QSettings()
        S.setValue("QRealTime/", self.parent.parent().currentIndex())
        for row in range (0,self.rowCount()):
            S.setValue("QRealTime/%s/%s/" % (self.service_id,self.item(row,0).text()),self.item(row,1).text())
        
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
        method='GET'
        url=self.getValue('url')+'/v1'+'/forms'
        print (url)
        status='not able to download'
        try:
            response= requests.get(url,headers=self.getAuth(),verify=False)
            forms=response.json()
            keylist= [form["xmlFormId"] for form in forms]
            print('keylist is',keylist)
            return keylist,response
        except:
            print ('getformList','not able to get the forms')
            return [''],status
    
            
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
            url = self.getValue('url')+'/v1'+'/forms'
        else:
            message= 'Created new form'
            method = 'POST'
            url = self.getValue('url')+'/v1/forms'
#        method = 'POST'
#        url = self.getValue('url')+'//formUpload'
        #step1 - upload form: POST if new PATCH if exixtent
        with open(xForm,'r') as myfile:
            xml= myfile.read()
        headers=self.getAuth()
        headers['Content-Type']= 'application/xml'
        print('header is',headers)
        response = requests.post(url,data=xml, proxies = getProxiesConf(),headers=headers,verify=False )
        if response.status_code== 201 or response.status_code == 200:
            self.iface.messageBar().pushSuccess(self.tr("QRealTime plugin"),
                                                self.tr('Layer is online('+message+'), Collect data from App'))
        elif response.status_code == 409:
            self.iface.messageBar().pushWarning(self.tr("QRealTime plugin"),self.tr("Form exist and can not be updated"))
        else:
            self.iface.messageBar().pushCritical(self.tr("QRealTime plugin"),self.tr("Form is not sent "))
        return response
        
    def collectData(self,layer,xFormKey,importData=False,topElement='',version='null',geoField=''):
#        if layer :
#            print("layer is not present or not valid")
#            return
        self.updateFields(layer)
        if importData:
            response, remoteTable = self.getTable(xFormKey,"",topElement,version)
        else:
            response, remoteTable = self.getTable(xFormKey,self.getValue('lastID'),topElement,version)
        if response.status_code == 200:
            print ('before Update Layer')
            if remoteTable:
                print ('table have some data')
                self.updateLayer(layer,remoteTable,geoField)
        else:
            self.iface.messageBar().pushCritical(self.tr("QRealTime plugin"),self.tr("Not able to collect data from Aggregate"))
    
    def updateFields(self,layer,text='ODKUUID',q_type=QVariant.String,config={}):
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
    def updateLayer(self,layer,dataDict,geoField=''):
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
                if not odkFeature['ODKUUID'] in uuidList:
                    qgisFeature = QgsFeature()
                    wktGeom = self.guessWKTGeomType(odkFeature[geoField])
                    print (wktGeom)
                    if wktGeom[:3] != layerGeo[:3]:
                        continue
                    qgisGeom = QgsGeometry.fromWkt(wktGeom)
                    print('geom is',qgisGeom)
                    qgisFeature.setGeometry(qgisGeom)
                    qgisFeature.initAttributes(len(QgisFieldsList))
                    for fieldName, fieldValue in six.iteritems(odkFeature):
                        if fieldName != geoField:
                            try:
                                qgisFeature.setAttribute(QgisFieldsList.index(fieldName),fieldValue)
                            except:
                                fieldError = fieldName
                            
                    newQgisFeatures.append(qgisFeature)
            except:
                    print('unable to create geometry Field')
                
                
        if fieldError:
            self.iface.messageBar().pushWarning(self.tr("QRealTime plugin"), self.tr("Can't find '%s' field") % fieldError)
        
        with edit(layer):
            layer.addFeatures(newQgisFeatures)
        self.processingLayer = None
        
    def getUUIDList(self,lyr):
        uuidList = []
        if lyr:
            uuidFieldName = None
            for field in lyr.fields():
                if 'UUID' in field.name().upper():
                    uuidFieldName = field.name()
            if uuidFieldName:
                for qgisFeature in lyr.getFeatures():
                    uuidList.append(qgisFeature[uuidFieldName])
        return uuidList

    def guessWKTGeomType(self,geom):
        if geom:
            coordinates = geom.split(';')
        else:
            return 'error'
#        print ('coordinates are '+ coordinates)
        firstCoordinate = coordinates[0].strip().split(" ")
#        print ('first Coordinate is '+  firstCoordinate)
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
        url=self.getValue('url')+'/v1/forms/'+XFormKey+'/submissions'
        print('inside getTable',url)
        method='GET'
        table=[]
        response = requests.request(method,url,proxies=getProxiesConf(),headers=self.getAuth(),verify=False)
        if not response.status_code == 200:
                return response, table
        try:
            submissions= response.json()
            instances={instance['instanceId']:instance['xml'] for instance in submissions}
            no_sub= len(instances)
            print('instance ids before filter',instances)
            print('number of submissions are',no_sub)
            print('downloading')
            ns='{http:opendatakit.org/submissions}'
            for id,xml in instances.items() :
                if id:
                    print ('xml downlaoded is',xml)
                    data=ET.fromstring(xml)
                    print('downloaded data is',data)
                    dict={child.tag:child.text for child in data}
                    print('dictionary is',dict)
                    for key,value in dict.items():
                                if value is None:
                                    grEle=data.findall(key)
                                    try:
                                        for child in grEle[0]:
                                            dict[child.tag]=child.text
                                            print('found a group element')
                                    except:
                                        print('error')
                    urlAttachments= url+'/'+id+'/attachments'
                    headers= self.getAuth()
                    res=requests.get(urlAttachments,proxies=getProxiesConf(),headers=headers,verify=False)
                    mediaFiles=res.json()
                    print('mediaFiles are',mediaFiles)
                    for mediaFile in mediaFiles:
                        for key,value in dict.items():
                            print('value is',value)
                            if value==mediaFile:
                                murl= urlAttachments+'/'+mediaFile
                                print('Download url is',murl)
                                dict[key]= murl
                    table.append(dict)
            print ('table is:',table)
            return response, table
        except Exception as e:
            print ('not able to fetch',e)
            return response,table
