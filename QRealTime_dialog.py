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

from PyQt4 import QtGui, uic
from PyQt4.QtGui import  QWidget,QTableWidget,QTableWidgetItem
from PyQt4.QtCore import Qt, QSettings, QSize, QSettings
from qgis.core import QgsFeature, QgsGeometry, QgsField, QgsPoint, QgsCoordinateReferenceSystem, QgsCoordinateTransform
import xml.etree.ElementTree as ET
import requests
from qgis.gui import QgsMessageBar

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
class QRealTimeDialog(QtGui.QDialog, FORM_CLASS):
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
        ["lastID",''],
        ["user", ''],
        ["password", '']
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
        
    def getFormList(self,xForm_id):
        method='GET'
        url=self.getValue('url')+'//formList'
        response= requests.request(method,url)
        root=ET.fromstring(response.content)
        keylist=[form.attrib['url'].split('=')[1] for form in root.findall('form')]
        return xForm_id in keylist, response
            
    def sendForm(self, xForm_id,xForm):
        
#        step1 - verify if form exists:
        form_key, response = self.getFormList(xForm_id)
        if response.status_code != requests.codes.ok:
            return response
        if form_key:
            method = 'POST'
            url = self.getValue('url')+'//formUpload'
        else:
            method = 'POST'
            url = self.getValue('url')+'//formUpload'
#        method = 'POST'
#        url = self.getValue('url')+'//formUpload'
        #step1 - upload form: POST if new PATCH if exixtent
        files = open(xForm,'r')
        files = {'form_def_file':files }
        response = requests.request(method, url,files = files, proxies = getProxiesConf() )
        return response
        
    def collectData(self,layer):
        if not layer :
            return
        self.updateFields(layer)
        XFormKey=layer.name()
        response, remoteTable = self.getTable(XFormKey)
        if response.status_code == 200:
            print 'before Update Layer'
            if remoteTable:
                print 'table have some data'
                self.updateLayer(layer,remoteTable)
        else:
            self.iface.messageBar().pushMessage(self.tr("QGISODK plugin"),
                                                self.tr("Form is invalid"),
                                                level=QgsMessageBar.CRITICAL, duration=6)
    
    def updateFields(self,layer):
        flag=True
        for field in layer.pendingFields():
            if field.name() == 'ODKUUID':
                flag=False
        if flag:
            uuidField = QgsField("ODKUUID", QVariant.String)
            uuidField.setLength(50)
            layer.dataProvider().addAttributes([uuidField])
            layer.updateFields()

    
    def updateLayer(self,layer,dataDict):
        #print "UPDATING N.",len(dataDict),'FEATURES'
        self.processingLayer = layer
        QgisFieldsList = [field.name() for field in layer.pendingFields()]
        #layer.beginEditCommand("ODK syncronize")
        layer.startEditing()
        
        uuidList = self.getUUIDList(self.processingLayer)

        newQgisFeatures = []
        fieldError = None
        for odkFeature in dataDict:
            if not odkFeature['ODKUUID'] in uuidList:
                qgisFeature = QgsFeature()
                wktGeom = self.guessWKTGeomType(odkFeature['GEOMETRY'])
                qgisGeom = QgsGeometry.fromWkt(wktGeom)
                qgisFeature.setGeometry(qgisGeom)
                qgisFeature.initAttributes(len(QgisFieldsList))
                for fieldName, fieldValue in odkFeature.iteritems():
                    if fieldName != 'GEOMETRY':
                        try:
                            qgisFeature.setAttribute(QgisFieldsList.index(fieldName),fieldValue)
                        except:
                            fieldError = fieldName
                        
                newQgisFeatures.append(qgisFeature)
                
        if fieldError:
            self.iface.messageBar().pushMessage(self.tr("QGISODK plugin"), self.tr("Can't find '%s' field") % fieldError, level=QgsMessageBar.WARNING, duration=6)
        
        layer.addFeatures(newQgisFeatures)
        self.processingLayer = None
    def getUUIDList(self,lyr):
        uuidList = []
        if lyr:
            uuidFieldName = None
            for field in lyr.pendingFields():
                if 'UUID' in field.name().upper():
                    uuidFieldName = field.name()
            if uuidFieldName:
                for qgisFeature in lyr.getFeatures():
                    uuidList.append(qgisFeature[uuidFieldName])
        return uuidList

    def guessWKTGeomType(self,geom):
        coordinates = geom.split(';')
        firstCoordinate = coordinates[0].strip().split(" ")
        if len(firstCoordinate) < 2:
            return "invalid", None
        coordinatesList = []
        for coordinate in coordinates:
            decodeCoord = coordinate.strip().split(" ")
            coordinatesList.append([decodeCoord[0],decodeCoord[1]])
        if len(coordinates) == 1:
            
            reprojectedPoint = self.transformToLayerSRS(QgsPoint(float(coordinatesList[0][1]),float(coordinatesList[0][0])))
            return "POINT(%s %s)" % (reprojectedPoint.x(), reprojectedPoint.y()) #geopoint
        else:
            coordinateString = ""
            for coordinate in coordinatesList:
                reprojectedPoint = self.transformToLayerSRS(QgsPoint(float(coordinate[1]), float(coordinate[0])))
                coordinateString += "%s %s," % (reprojectedPoint.x(), reprojectedPoint.y())
            coordinateString = coordinateString[:-1]
        if coordinates[-1] == '' and coordinatesList[0][0] == coordinatesList[-2][0] and coordinatesList[0][1] == coordinatesList[-2][1]:
            return "POLYGON(%s)" % coordinateString #geoshape #geotrace
        else:
            return "LINESTRING(%s)" % coordinateString
            
    def transformToLayerSRS(self, pPoint):
        # transformation from the current SRS to WGS84
        crsDest = self.processingLayer.crs () # get layer crs
        crsSrc = QgsCoordinateReferenceSystem(4326)  # WGS 84
        xform = QgsCoordinateTransform(crsSrc, crsDest)
        return xform.transform(pPoint)


        
                                                
    def getTable(self,XFormKey):
        url=self.getValue('url')+'/view/submissionList?formId='+XFormKey
        method='GET'
        table=[]
        response = requests.request(method,url,proxies=getProxiesConf())
        if not response.status_code == 200:
                return response, table
        try:
            root = ET.fromstring(response.content)
            ns='{http://opendatakit.org/submissions}'
            instance_ids=[child.text for child in root[0].findall(ns+'id')]
            print 'instance ids before filter', instance_ids
            ns1='{http://www.opendatakit.org/cursor}'
            lastReturnedURI= ET.fromstring(root[1].text).findall(ns1+'uriLastReturnedValue')[0].text
            print 'server lastID is',lastReturnedURI
        
            lastID= self.getValue('lastID')
            print 'lastID is',lastID
            if lastID ==lastReturnedURI:
                print 'No Download returning'
                return response,table
            lastindex=0
            try:
                lastindex= instance_ids.index(lastID)
            except:
                print 'first Download'
            instance_ids=instance_ids[lastindex:]
            print  'downloading',instance_ids
            for id in instance_ids :
                if id:
                    url=self.getValue('url')+'/view/downloadSubmission?formId={}[@version=null and @uiVersion=null]/{}[@key={}]'.format(XFormKey,XFormKey,id)
                    response=requests.request(method,url)
                    if not response.status_code == 200:
                        return response,table
                    root1=ET.fromstring(response.content)
                    data=root1[0].findall(ns+XFormKey)
                    dict={child.tag.replace(ns,''):child.text for child in data[0]}
                    mediaFile=root1.findall(ns+'mediaFile')
                    if len(mediaFile)>0:
                        mediaDict={child.tag.replace(ns,''):child.text for child in mediaFile[0]}
                        for key,value in dict.iteritems():
                            if value==mediaDict['filename']:
                                dict[key]=self.cleanURI(mediaDict['downloadUrl'],XFormKey,value)
                    table.append(dict)
            self.getValue('lastID',lastReturnedURI)
            return response, table
        except:
            print 'not able to fetch'
        
        
        
    def cleanURI(self,URI,layerName,fileName):
            
            attachements = {}
            if isinstance(URI, basestring) and (URI[0:7] == 'http://' or URI[0:8] == 'https://'):
                downloadDir = os.path.join(os.path.expanduser('~'),'attachments_%s' % layerName)
                if not os.path.exists(downloadDir):
                    os.makedirs(downloadDir)
                try:
                    response = requests.get(URI, stream=True)
                except:
                    sys.exit()
                localAttachmentPath = os.path.abspath(os.path.join(downloadDir,fileName))
                if response.status_code == 200:
                    print "downloading", URI
                    with open(localAttachmentPath, 'wb') as f:
                        for chunk in response:
                            f.write(chunk)
                        localURI = localAttachmentPath
                    print 'loaded image'
                    print localURI
                    return localURI
                    
                else:
                    print 'error downloading remote file: ',response.reason
                    return 'error downloading remote file: ',response.reason
            else:
                print 'Not downloaded anything'
                return URI

