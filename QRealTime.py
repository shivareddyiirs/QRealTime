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

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication,QVariant
from PyQt4.QtGui import QMenu, QAction, QIcon, QFileDialog

# import for XML reading writing
from pyxform.builder import create_survey_element_from_dict
# Import the code for the dialog
from QRealTime_dialog import QRealTimeDialog, aggregate
import os.path
from qgis.core import QgsMapLayer
import warnings
import unicodedata
import re

def slugify(s):
    if type(s) is unicode:
        slug = unicodedata.normalize('NFKD', s)
    elif type(s) is str:
        slug = s
    else:
        raise AttributeError("Can't slugify string")
    slug = slug.encode('ascii', 'ignore').lower()
    slug = re.sub(r'[^a-z0-9]+', '-', slug).strip('-')
    slug=re.sub(r'--+',r'-',slug)
    return slug
    
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
        locale = QSettings().value('locale/userLocale')[0:2]
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
        self.menu = self.tr(u'&QGIS_Real_Time')
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

        icon_path = ':/plugins/QRealTime/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'QRealTimeSetting'),
            callback=self.run,
            parent=self.iface.mainWindow())
        icon = QIcon(icon_path)
        self.ODKMenu = QMenu('QRealTime')
        self.sync= QAction(self.tr(u'sync'),self.ODKMenu)
        self.sync.setCheckable(True)
        self.sync.toggled.connect(self.download)
        self.iface.legendInterface().addLegendLayerAction(
            self.sync,
            "",
            "01", 
            QgsMapLayer.VectorLayer,
            True)
        self.makeOnline=QAction(self.tr(u'Make Online'),self.ODKMenu)
        self.makeOnline.triggered.connect(self.sendForm)
        self.iface.legendInterface().addLegendLayerAction(
            self.makeOnline,
            '',
            '01',
            QgsMapLayer.VectorLayer,
            True)


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'QGIS_Real_Time'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        self.iface.legendInterface().removeLegendLayerAction(self.sync)
        self.iface.legendInterface().removeLegendLayerAction(self.makeOnline)
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
            
    def getLayer(self):
        return self.iface.legendInterface().currentLayer()
        
    def sendForm(self):
#        get the fields model like name , widget type, options etc.
        layer=self.getLayer()
        fieldDict= self.getFieldsModel(layer)
        surveyDict= {"name":slugify(layer.name()),"title":layer.name(),"instance_name": 'uuid()',"submission_url": '',
        "default_language":'default','id_string':slugify(layer.name()),'type':'survey','children':fieldDict }
        survey=create_survey_element_from_dict(surveyDict)
        xml=survey.to_xml(validate=None, warnings=warnings)
        os.chdir(os.path.expanduser('~'))
        with open('Xform.xml','w') as xForm:
            xForm.write(xml)
        self.dlg.getCurrentService().sendForm(layer,'Xform.xml')
    def download(self,checked=False):
        if checked==True:
            self.dlg.getCurrentService().collectData(self.getLayer())
            
    def getFieldsModel(self,currentLayer):
        currentFormConfig = currentLayer.editFormConfig()
        fieldsModel = []
        i=0
        for field in currentLayer.pendingFields():
            fieldDef = {}
            fieldDef['name'] = field.name()
            fieldDef['map'] = field.name()
            fieldDef['label'] = field.comment() or field.name()
            fieldDef['hint'] = ''
            fieldDef['type'] = self.QVariantToODKtype(field.type())
            fieldDef['fieldEnabled'] = True
            fieldDef['bind'] = {}
            fieldDef['fieldDefault'] = ''
            fieldDef['fieldWidget'] = currentFormConfig.widgetType(i)
            if fieldDef['fieldWidget'] == 'Hidden':
                fieldDef['fieldEnabled'] = None
            else:
                fieldDef['fieldEnabled'] = True
            if fieldDef['fieldWidget'] in ('ValueMap','CheckBox','Photo','FileName'):
                if fieldDef['fieldWidget'] == 'ValueMap':
                    config = {v: k for k, v in currentFormConfig.widgetConfig(i).iteritems()}
                else:
                    config = currentFormConfig.widgetConfig(i)
                fieldDef['choices'] = config
            else:
                fieldDef['choices'] = {}
            if fieldDef['name'] == 'ODKUUID':
                fieldDef["bind"] = {"readonly": "true()", "calculate": "concat('uuid:', uuid())"}
            fieldsModel.append(fieldDef)
            i+=1
        return fieldsModel
    def QVariantToODKtype(self,q_type):
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
