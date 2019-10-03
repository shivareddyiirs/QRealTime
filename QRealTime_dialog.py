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
import datetime
try:
        from pyxform.builder import create_survey_element_from_dict
        print('package already installed')
except ImportError:
    try:
        subprocess.call(['python3', '-m', 'pip', 'install','pyxform'])
        from pyxform.builder import create_survey_element_from_dict
        print('package is installed after python3')
    except:
        subprocess.call(['python3', '-m', 'pip', 'install','pyxform','--user'])
        print ("after python3 --user call")
        try:
            from pyxform.builder import create_survey_element_from_dict
        except:
            print('not able to install pyxform, install mannually') 
tag='QRealTime'
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
        auth = requests.auth.HTTPDigestAuth(self.getValue('user'),self.getValue('password'))
        return auth

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
        url=self.getValue('url')+'//formList'
        response= requests.request(method,url,auth=self.getAuth(),verify=False)
        root=ET.fromstring(response.content)
        keylist=[form.attrib['url'].split('=')[1] for form in root.findall('form')]
        return keylist,response
    def importData(self,layer,selectedForm):
        url=self.getValue('url')+'//formXml?formId='+selectedForm
        response= requests.request('GET',url,proxies=getProxiesConf(),auth=self.getAuth(),verify=False)
        if response.status_code==200:
            # with open('importForm.xml','w') as importForm:
            #     importForm.write(response.content)
            self.formKey,self.topElement,self.version,self.geoField = self.updateLayerXML(layer,response.content)
            layer.setName(self.formKey)
            self.collectData(layer,self.formKey,True,self.topElement,self.version,self.geoField)
        else:
            print("unable to connect to server")
    def getFieldsModel(self,currentLayer):
        fieldsModel = []
        g_type= currentLayer.geometryType()
        fieldDef={'name':'GEOMETRY','type':'geopoint','bind':{'required':'true()'}}
        fieldDef['Appearance']= 'maps'
        if g_type==0:
            fieldDef['label']='add point location'
        elif g_type==1:
            fieldDef['label']='Draw Line'
            fieldDef['type']='geotrace'
        else:
            fieldDef['label']='Draw Area'
            fieldDef['type']='geoshape'
        fieldsModel.append(fieldDef)
        i=0
        for field in currentLayer.fields():
            widget =currentLayer.editorWidgetSetup(i)
            fwidget = widget.type()
            if (fwidget=='Hidden'):
                i+=1
                continue
                
            fieldDef = {}
            fieldDef['name'] = field.name()
            fieldDef['map'] = field.name()
            fieldDef['label'] = field.alias() or field.name()
            fieldDef['hint'] = ''
            fieldDef['type'] = QVariantToODKtype(field.type())
            fieldDef['bind'] = {}
#            fieldDef['fieldWidget'] = currentFormConfig.widgetType(i)
            fieldDef['fieldWidget']=widget.type()
            print('getFieldModel',fieldDef['fieldWidget'])
            if fieldDef['fieldWidget'] in ('ValueMap','CheckBox','Photo','ExternalResource'):
                if fieldDef['fieldWidget'] == 'ValueMap':
                    fieldDef['type']='select one'
                    valueMap=widget.config()['map']
                    config={}
                    for value in valueMap:
                        for k,v in value.items():
                                config[v]=k
                    print('configuration is ',config)
                    choicesList=[{'name':name,'label':label} for name,label in config.items()]
                    fieldDef["choices"] = choicesList
                elif fieldDef['fieldWidget'] == 'Photo' or fieldDef['fieldWidget'] == 'ExternalResource' :
                    fieldDef['type']='image'
                    print('got an image type field')
                
#                fieldDef['choices'] = config
            else:
                fieldDef['choices'] = {}
            if fieldDef['name'] == 'ODKUUID':
                fieldDef["bind"] = {"readonly": "true()", "calculate": "concat('uuid:', uuid())"}
            if fieldDef['fieldWidget'] == 'DateTime':
                fieldDef["type"] = 'date'
            fieldsModel.append(fieldDef)
            i+=1
        return fieldsModel
    def updateLayerXML(self,layer,xml):
        ns='{http://www.w3.org/2002/xforms}'
        root= ET.fromstring(xml)
        #key= root[0][1][0][0].attrib['id']
        instance=root[0][1].find(ns+'instance')
        key=instance[0].attrib['id']
        #topElement=root[0][1][0][0].tag.split('}')[1]
        topElement=instance[0].tag.split('}')[1]
        try:
            version=instance[0].attrib['version']
        except:
            version='null'
        print('key captured'+ key)
        print (root[0][1].findall(ns+'bind'))
        for bind in root[0][1].findall(ns+'bind'):
            attrib=bind.attrib
            print (attrib)
            fieldName= attrib['nodeset'].split('/')[-1]
            fieldType=attrib['type']
            print('attrib type is',attrib['type'])
            qgstype,config = qtype(attrib['type'])
            print ('first attribute'+ fieldName)
            inputs=root[1].findall('.//*[@ref]')
            if fieldType[:3]!='geo':
                print('creating new field:'+ fieldName)
                isHidden= True
                for input in inputs:
                    if fieldName == input.attrib['ref'].split('/')[-1]:
                        isHidden= False
                        break
                if isHidden:
                    print('Reached Hidden')
                    config['type']='Hidden'
                self.updateFields(layer,fieldName,qgstype,config)
            else:
                geoField=fieldName
        return key,topElement,version,geoField
    def prepareForm(self,layer,out):
        version= str(datetime.date.today())
        fieldDict= self.getFieldsModel(layer)
        print ('fieldDict',fieldDict)
        surveyDict= {"name":layer.name(),"title":layer.name(),'VERSION':version,"instance_name": 'uuid()',"submission_url": '',
        "default_language":'default','id_string':layer.name(),'type':'survey','children':fieldDict }
        survey=create_survey_element_from_dict(surveyDict)
        xml=survey.to_xml(validate=None, warnings='warnings')
        os.chdir(os.path.expanduser('~'))
        with open(out,'w') as xForm:
            xForm.write(xml)    
    def sendForm(self,xForm_id,xForm):
#        step1 - verify if form exists:
        formList, response = self.getFormList()
        form_key=xForm_id in formList
        if response.status_code != requests.codes.ok:
            return response
        message =''
        if form_key:
            message= 'Form Updated'
            method = 'POST'
            url = self.getValue('url')+'//formUpload'
        else:
            message= 'Created new form'
            method = 'POST'
            url = self.getValue('url')+'//formUpload'
#        method = 'POST'
#        url = self.getValue('url')+'//formUpload'
        #step2 - upload form
        files = open(xForm,'r')
        files = {'form_def_file':files }
        response = requests.request(method, url,files = files, proxies = getProxiesConf(),auth=self.getAuth(),verify=False )
        if response.status_code== 201:
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
                uuidField.setLength(300)
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
        print('geofield is',geoField)
        for odkFeature in dataDict:
            id=None
            try:
                id= odkFeature['ODKUUID']
            except:
                print('error in reading ODKUUID')
            try:
                if not id in uuidList:
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
            except Exception as e:
                    print('unable to create',e)
                
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
        url=self.getValue('url')+'/view/submissionList?formId='+XFormKey
        method='GET'
        table=[]
        response = requests.request(method,url,proxies=getProxiesConf(),auth=self.getAuth(),verify=False)
        if not response.status_code == 200:
                return response, table
        try:
            root = ET.fromstring(response.content)
            ns='{http://opendatakit.org/submissions}'
            instance_ids=[child.text for child in root[0].findall(ns+'id')]
            no_sub= len(instance_ids)
#            print('instance ids before filter',instance_ids)
            print('number of submissions are',no_sub)
            ns1='{http://www.opendatakit.org/cursor}'
            lastReturnedURI= ET.fromstring(root[1].text).findall(ns1+'uriLastReturnedValue')[0].text
            print('server lastID is', lastReturnedURI)
            if lastID ==lastReturnedURI:
                print ('No Download returning')
                return response,table
            lastindex=0
            try:
                lastindex= instance_ids.index(lastID)
            except:
                print ('first Download')
            instance_ids=instance_ids[lastindex:]
            print('downloading')
            for id in instance_ids :
                if id:
                    url=self.getValue('url')+'/view/downloadSubmission'
                    print (url)
                    para={'formId':'{}[@version={} and @uiVersion=null]/{}[@key={}]'.format(XFormKey,version,topElement,id)}
                    response=requests.request(method,url,params=para,proxies=getProxiesConf(),auth=self.getAuth(),verify=False)
                    if not response.status_code == 200:
                        return response,table
                    print('xml downloaded is',response.content)
                    root1=ET.fromstring(response.content)
                    print('downloaded data is',root1)
                    data=root1[0].findall(ns+topElement)
                    print('data is',data[0])
                    dict={child.tag.split('}')[-1]:child.text for child in data[0]}
                    dict['ODKUUID']=id
                    print('dictionary is',dict)
                    dict2= dict.copy()
                    for key,value in six.iteritems(dict2):
                                if value is None:
                                    grEle=data[0].findall(ns+key)
                                    try:
                                        for child in grEle[0]:
                                            dict[child.tag.split('}')[-1]]=child.text
                                            print('found a group element')
                                    except:
                                        print('error')
                    mediaFiles=root1.findall(ns+'mediaFile')
                    if len(mediaFiles)>0:
                        for mediaFile in mediaFiles:
                            mediaDict={child.tag.replace(ns,''):child.text for child in mediaFile}
                            for key,value in six.iteritems(dict):
                                print('value is',value)
                                if value==mediaDict['filename']:
                                    murl= mediaDict['downloadUrl']
                                    print('Download url is',murl)
                                    if murl.endswith('as_attachment=true'):
                                        murl=murl[:-19]
                                        dict[key]= murl
                    table.append(dict)
            self.getValue('lastID',lastReturnedURI)
            print ('table is:',table)
            return response, table
        except Exception as e:
            print ('not able to fetch',e)
            return response,table
