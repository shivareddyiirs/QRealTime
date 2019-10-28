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
from PyQt5.QtWidgets import QWidget,QTableWidget,QTableWidgetItem
from PyQt5.QtCore import Qt, QSettings, QSize,QVariant
import xml.etree.ElementTree as ET
import requests
from qgis.gui import QgsMessageBar
from qgis.core import QgsProject,QgsFeature,QgsGeometry,QgsField, QgsCoordinateReferenceSystem, QgsPoint, QgsCoordinateTransform,edit,QgsPointXY,QgsEditorWidgetSetup
import six
from six.moves import range
from qgis.core import QgsMessageLog, Qgis
import datetime
import subprocess
import json
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
debug=True
tag="QRealTime"
def print(text,opt=None):
    """ to redirect print to MessageLog"""
    if debug:
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
    services = ['Aggregate','Kobo']
    def __init__(self, caller,parent=None):
        """Constructor."""
        super(QRealTimeDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        i=0
        for service in self.services:
            if i>0:
                container = QWidget()
                container.resize(QSize(310,260))
                self.tabServices.addTab(container,"")
            container = self.tabServices.widget(i)
            print (container)
            serviceClass = globals()[service]
            serviceClass(container,caller)
            self.tabServices.setTabText(i, service)
            i=i+1
    
    def getCurrentService(self):
        return self.tabServices.currentWidget().children()[0]

class Aggregate (QTableWidget):
    parameters = [
        ["id","Aggregate"],
        ["url",''],
        ["user", ''],
        ["password", ''],
        ["lastID",''],
        ['sync time',3600]
        ]
    tag='ODK Aggregate'
    def __init__(self,parent,caller):
        super(Aggregate, self).__init__(parent)
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
                value=self.item(row,1).text().strip()
                if value:
                    return value
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
     

#    def getExportExtension(self):
#        return 'xml'
        
    def getFormList(self):
        method='GET'
        url=self.getValue('url')
        if url:
            furl=url+'//formList'
        else:
            self.iface.messageBar().pushWarning(self.tr(self.tag),self.tr("Enter url in settings"))
            return {},None
        try:
            response= requests.request(method,furl,auth=self.getAuth(),verify=False)
        except:
            self.iface.messageBar().pushWarning(self.tr(self.tag),self.tr("Not able to connect to server"))
            return {},None
        if response.status_code==200:
            root=ET.fromstring(response.content)
            keylist=[form.attrib['url'].split('=')[1] for form in root.findall('form')]
            forms= {key:key for key in keylist}
            return forms,response
    def importData(self,layer,selectedForm,importData):
        url=self.getValue('url')
        if url:
            furl=url+'//formXml?formId='+selectedForm
        else:
            self.iface.messageBar().pushWarning(self.tr(self.tag),self.tr("Enter url in settings"))
            return
        try:
            response= requests.request('GET',furl,proxies=getProxiesConf(),auth=self.getAuth(),verify=False)
        except:
            self.iface.messageBar().pushWarning(self.tr(self.tag),self.tr("Not able to connect to server"))
            return
        if response.status_code==200:
            # with open('importForm.xml','w') as importForm:
            #     importForm.write(response.content)
            self.formKey,self.topElement,self.version,self.geoField = self.updateLayerXML(layer,response.content)
            layer.setName(self.formKey)
            self.collectData(layer,self.formKey,importData,self.topElement,self.version,self.geoField)
        else:
            self.iface.messageBar().pushWarning(self.tr(self.tag),self.tr("Not able to coleect data from server"))
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
    def prepareSendForm(self,layer):
        self.updateFields(layer)
        version= str(datetime.date.today())
        fieldDict= self.getFieldsModel(layer)
        print ('fieldDict',fieldDict)
        surveyDict= {"name":layer.name(),"title":layer.name(),'VERSION':version,"instance_name": 'uuid()',"submission_url": '',
        "default_language":'default','id_string':layer.name(),'type':'survey','children':fieldDict }
        survey=create_survey_element_from_dict(surveyDict)
        xml=survey.to_xml(validate=None, warnings='warnings')
        os.chdir(os.path.expanduser('~'))
        self.sendForm(layer.name(),xml)  
    def sendForm(self,xForm_id,xml):
#        step1 - verify if form exists:
        formList, response = self.getFormList()
        form_key = xForm_id in formList
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
        with open('xForm.xml','w')as xForm:
            xForm.write(xml)
        file = open('xForm.xml','r')
        files = {'form_def_file':file}
        response = requests.request(method, url,files = files, proxies = getProxiesConf(),auth=self.getAuth(),verify=False )
        if response.status_code== 201:
            self.iface.messageBar().pushSuccess(self.tr(self.tag),
                                                self.tr('Layer is online('+message+'), Collect data from App'))
        elif response.status_code == 409:
            self.iface.messageBar().pushWarning(self.tr(self.tag),self.tr("Form exist and can not be updated"))
        else:
            self.iface.messageBar().pushCritical(self.tr(self.tag),self.tr("Form is not sent "))
        file.close()
        return response
        
    def collectData(self,layer,xFormKey,importData=False,topElement='',version='null',geoField=''):
#        if layer :
#            print("layer is not present or not valid")
#            return
        self.updateFields(layer)
        response, remoteTable = self.getTable(xFormKey,importData,topElement,version)
        if response.status_code == 200:
            print ('before Update Layer')
            if remoteTable:
                print ('table have some data')
                self.updateLayer(layer,remoteTable,geoField)
        else:
            self.iface.messageBar().pushCritical(self.tr(self.tag),self.tr("Not able to collect data from Aggregate"))
    
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
        except Exception as e:
            print(e)
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
            print(odkFeature)
            id=None
            try:
                id= odkFeature['ODKUUID']
                print('odk id is',id)
            except:
                print('error in reading ODKUUID')
            try:
                if not id in uuidList:
                    qgisFeature = QgsFeature()
                    print(odkFeature)
                    wktGeom = self.guessWKTGeomType(odkFeature[geoField])
                    print (wktGeom)
                    if wktGeom[:3] != layerGeo[:3]:
                        print(wktGeom,'is not matching'+layerGeo)
                        continue
                    qgisGeom = QgsGeometry.fromWkt(wktGeom)
                    print('geom is',qgisGeom)
                    qgisFeature.setGeometry(qgisGeom)
                    qgisFeature.initAttributes(len(QgisFieldsList))
                    for fieldName, fieldValue in odkFeature.items():
                        if fieldName != geoField:
                            try:
                                qgisFeature.setAttribute(QgisFieldsList.index(fieldName),fieldValue)
                            except:
                                fieldError = fieldName
                            
                    newQgisFeatures.append(qgisFeature)
            except Exception as e:
                    print('unable to create',e)
                
        if fieldError:
            self.iface.messageBar().pushWarning(self.tr(self.tag), self.tr("Can't find '%s' field") % fieldError)
        
        with edit(layer):
            layer.addFeatures(newQgisFeatures)
        self.processingLayer = None
        
    def getUUIDList(self,lyr):
        uuidList = []
        uuidFieldName=None
        QgisFieldsList = [field.name() for field in lyr.fields()]
        for field in QgisFieldsList:
            if 'UUID' in field:
                uuidFieldName =field
        if uuidFieldName:
            print(uuidFieldName)
            for qgisFeature in lyr.getFeatures():
                uuidList.append(qgisFeature[uuidFieldName])
        print (uuidList)
        return uuidList
            
    def transformToLayerSRS(self, pPoint):
        # transformation from the current SRS to WGS84
        crsDest = self.processingLayer.crs () # get layer crs
        crsSrc = QgsCoordinateReferenceSystem(4326)  # WGS 84
        xform = QgsCoordinateTransform(crsSrc, crsDest, QgsProject.instance())
        try:
            return QgsPoint(xform.transform(pPoint))
        except :
            return QgsPoint(xform.transform(QgsPointXY(pPoint)))


        
                                                
    def getTable(self,XFormKey,importData,topElement,version= 'null'):
        turl=self.getValue('url')
        table=[]
        if turl:
            url=turl+'/view/submissionList?formId='+XFormKey
        else:
            self.iface.messageBar().pushWarning(self.tr(self.tag),self.tr("Enter url in settings"))
            return None,table
        method='GET'
        lastID=""
        if not importData:
            lastID=self.getValue('lastID')
        try:
            response = requests.request(method,url,proxies=getProxiesConf(),auth=self.getAuth(),verify=False)
        except:
            self.iface.messageBar().pushCritical(self.tr(self.tag),self.tr("Not able to connect to server"))
            return response, table
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
                    #print('xml downloaded is',response.content)
                    root1=ET.fromstring(response.content)
                    #print('downloaded data is',root1)
                    data=root1[0].findall(ns+topElement)
                    #print('data is',data[0])
                    dict={child.tag.split('}')[-1]:child.text for child in data[0]}
                    dict['ODKUUID']=id
                    #print('dictionary is',dict)
                    dict2= dict.copy()
                    for key,value in dict2.items():
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
            #print ('table is:',table)
            return response, table
        except Exception as e:
            print ('not able to fetch',e)
            return response,table
class Kobo (Aggregate):
    parameters = [
        ["id","Kobo"],
        ["url",'https://kobo.humanitarianresponse.info/'],
        ["user", ''],
        ["password", ''],
        ["last Submission",''],
        ['sync time','']
        ]
    tag="KoboToobox"
    def __init__(self,parent,caller):
        super(Kobo, self).__init__(parent,caller)
    def prepareSendForm(self,layer):
        self.updateFields(layer)
        fieldDict,choicesList= self.getFieldsModel(layer)
        print ('fieldDict',fieldDict)
        payload={"uid":layer.name(),"name":layer.name(),"asset_type":"survey","content":json.dumps({"survey":fieldDict,"choices":choicesList})}
        print("Payload= ",payload)
        self.sendForm(layer.name(),payload)
    def sendForm(self,xForm_id,payload):

#        step1 - verify if form exists:
        formList, response = self.getFormList()
        form=''
        for item in formList:
            if formList[item]==xForm_id:
                form=xForm_id
                xForm_id=item
        if response.status_code != requests.codes.ok:
            print(status)
            return status
        message =''
        if form:
            message= 'Form Updated'
            method = 'POST'
            url = self.getValue('url')+'/assets/'+xForm_id
        else:
            message= 'Created new form'
            method = 'POST'
            url = self.getValue('url')+'/assets/'
        para = {"format":"json"}
        headers = {'Content-Type': "application/json",'Accept': "application/json"}
        #creates form:
        response = requests.request(method,url,json=payload,auth=(self.getValue('user'),self.getValue('password')),headers=headers,params=para)
        responseJson=json.loads(response.text)
        urlDeploy = self.getValue('url')+"/assets/"+responseJson['uid']+"/deployment/"
        payload2 = json.dumps({"active": True})
        #deploys form:
        response2 = requests.post(urlDeploy,data=payload2, auth=(self.getValue('user'),self.getValue('password')), headers=headers, params=para)
        urlShare = self.getValue('url')+"permissions/"
        permissions={"content_object":self.getValue('url')+"/assets/"+responseJson['uid']+"/","permission": "view_submissions","deny": False,"inherited": False,"user": "https://kobo.humanitarianresponse.info/users/AnonymousUser/"}
        #shares submissions publicly:
        response3 = requests.post(urlShare, json=permissions, auth=(self.getValue('user'),self.getValue('password')),headers=headers)
        if response.status_code== 201 or response.status_code == 200:
            self.iface.messageBar().pushSuccess(self.tr(self.tag),
                                                self.tr('Layer is online('+message+'), Collect data from App'))
        elif response.status_code == 409:
            self.iface.messageBar().pushWarning(self.tr(self.tag),self.tr("Form exist and can not be updated"))
        else:
            self.iface.messageBar().pushCritical(self.tr(self.tag),self.tr(str(response.status_code)))
        return response
    def getFormList(self):
        user=self.getValue('user')
        turl=self.getValue('url')
        if turl:
            url=turl+'/assets/'
        else:
            self.iface.messageBar().pushWarning(self.tr(self.tag),self.tr("Enter url in settings"))
            return {},None
#        print (url)
        para={'format':'json'}
        keyDict={}
        questions=[]
        try:
            response= requests.get(url,auth=(self.getValue('user'), self.getValue('password')),params=para)
            forms= response.json()
            for form in forms['results']:        
                if form['asset_type']=='survey' and form['deployment__active']==True:
                    keyDict[form['name']]=form['uid']
#            print('keyDict is',keyDict)
            return keyDict,response
        except:
            self.iface.messageBar().pushCritical(self.tr(self.tag),self.tr("Invalid url username or password"))
            return {},response
    def importData(self,layer,selectedForm,importData=True):
        #from kobo branchQH
        turl=self.getValue('url')
        if turl:
            url=turl+'/assets/'+selectedForm
        else:
            self.iface.messageBar().pushWarning(self.tr(self.tag),self.tr("Enter url in settings"))
        para={'format':'xml'}
        requests.packages.urllib3.disable_warnings()
        try:
            response= requests.request('GET',url,proxies=getProxiesConf(),auth=(self.getValue('user'), self.getValue('password')),verify=False,params=para)
        except:
            self.iface.messageBar().pushCritical(self.tr(self.tag),self.tr("Invalid url,username or password"))
        if response.status_code==200:
            xml=response.content
            # with open('importForm.xml','w') as importForm:
            #     importForm.write(response.content)
            self.layer_name,self.version, self.geoField,self.fields= self.updateLayerXML(layer,xml)
            layer.setName(self.layer_name)
            self.collectData(layer,selectedForm,importData,self.layer_name,self.version,self.geoField)
        else:
            self.iface.messageBar().pushWarning(self.tr(self.tag),self.tr("not able to connect to server"))
    def updateLayerXML(self,layer,xml):
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
            fieldName= attrib['nodeset'].split('/')[-1]
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
                    if fieldName == input.attrib['ref'].split('/')[-1]:
                        isHidden= False
                        break
                if isHidden:
                    print('Reached Hidden')
                    config['type']='Hidden'
            else:
                geoField=fieldName
                print('geometry field is =',fieldName)
            self.updateFields(layer,fieldName,qgstype,config)
        return layer_name,version,geoField,fields
    def getTable(self,XFormKey,importData,topElement,layer,version= 'null'):
        requests.packages.urllib3.disable_warnings()
        # kobo or custom url not working hence hard coded url is being used
        url='https://kc.humanitarianresponse.info/'
        print(url)
        lastSub=""
        if not importData:
            try:
                lastSub=self.getValue('last Submission')
            except:
                print("error")
        response = requests.get(url+'/api/v1/data',auth=(self.getValue('user'),self.getValue('password')),verify=False)
        if not response.status_code == 200:
                print (response.status_code)
        responseJSON=json.loads(response.text)
        formID=''
        subTimeList=[]
        geoField=''
        table=[]
        for form in responseJSON:
            if str(form['id_string'])==XFormKey:
                formID=str(form['id'])
                print("found the form"+XFormKey+"with id"+formID)
        para={"query":json.dumps({"_submission_time": {"$gt": lastSub}}) }
        urlData=url+'/api/v1/data/'+formID
        response = requests.get(urlData,auth=(self.getValue('user'),self.getValue('password')),params=para,verify=False)
        data=json.loads(response.text)
        for submission in data:
            submission['ODKUUID']=submission['meta/instanceID']
            subTime=submission['_submission_time']
            subTime_datetime=datetime.datetime.strptime(subTime,'%Y-%m-%dT%H:%M:%S')
            subTimeList.append(subTime_datetime)
            for key in list(submission):
                print(key)
                if key == self.geoField:
                    print (self.geoField)
                    continue
                if key not in self.fields:
                    submission.pop(key)
                else:
                    if self.fields[key]=="binary":
                        submission[key]=url+'/attachment/original?media_file='+self.getValue('user')+'/attachments/'+submission[key]
            table.append(submission)
        if subTimeList:
            lastSubmission=max(subTimeList)
            lastSubmission=datetime.datetime.strftime(lastSubmission,'%Y-%m-%dT%H:%M:%S')+"+0000"
            self.getValue('last Submission',lastSubmission)
        return response, table
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
                if value=="ODKUUID":
                    fieldDef.pop(key)
                    fieldDef.pop("type")
            fieldsModel.append(fieldDef)
            i+=1
        return fieldsModel,choicesList