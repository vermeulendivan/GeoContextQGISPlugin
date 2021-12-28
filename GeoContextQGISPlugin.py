# -*- coding: utf-8 -*-
"""
/***************************************************************************
 GeoContextQGISPlugin
                                 A QGIS plugin
 QGIS plugin to connect to GeoContext
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2021-11-22
        git sha              : $Format:%H$
        copyright            : (C) 2021 by Kartoza
        email                : divan@kartoza.com
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
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, Qt, QVariant
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QTableWidgetItem
from qgis.core import (QgsProject, QgsSettings, QgsVectorLayer, QgsField, QgsVectorFileWriter, 
                       QgsCoordinateTransformContext, QgsMapLayer,QgsCoordinateTransform,
                       QgsPluginLayerRegistry, QgsLayerTree, QgsMapLayer,QgsCoordinateReferenceSystem)
from qgis.gui import QgsMapToolEmitPoint
# Initialize Qt resources from file resources.py
from .resources import *

# Import the code for the DockWidget
from .GeoContextQGISPlugin_dockwidget import GeoContextQGISPluginDockWidget
import os.path

from .GeoContextQGISPlugin_options_dialog import OptionsDialog
from .GeoContextQGISPlugin_processing_dialog import ProcessingDialog

from coreapi import Client


class GeoContextQGISPlugin:
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
            'GeoContextQGISPlugin_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&GeoContext')
        self.toolbar = self.iface.addToolBar(u'GeoContextQGISPlugin')
        self.toolbar.setObjectName(u'GeoContextQGISPlugin')

        # INITIALIZING GeoContextQGISPlugin
        self.pluginIsActive = False
        self.dockwidget = None

        self.canvas = self.iface.mapCanvas()

        # Ensuring that the plugin reads decimal coordinates of longitude and latitude by setting the plugin
        # crs to EPSG:4326
        canvasCrs = self.canvasCrs()
        if canvasCrs != "EPSG:4326":
            QgsCoordinateTransform(QgsCoordinateReferenceSystem("EPSG:4326"),
                                   canvasCrs, QgsProject.instance())
            extMap = self.canvas.extent()
            
            self.canvas.setDestinationCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
            self.canvas.freeze(False)
            self.canvas.setExtent(extMap)

        self.point_tool = QgsMapToolEmitPoint(self.canvas)  # Enables the cursor tool for selecting locations

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
        return QCoreApplication.translate('GeoContextQGISPlugin', message)

    # Getting the canvas crs
    def canvasCrs(self):
        mapCanvas = self.iface.mapCanvas()
        crs = mapCanvas.mapSettings().destinationCrs()
        return crs

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

        icon_path = ':/plugins/GeoContextQGISPlugin/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'GeoContext'),
            callback=self.run,
            parent=self.iface.mainWindow(),
            add_to_menu=False,
            add_to_toolbar=True)

        self.add_action(
            icon_path,
            text=self.tr(u'Options'),
            callback=self.show_options,
            parent=self.iface.mainWindow(),
            add_to_menu=True,
            add_to_toolbar=False)

        self.add_action(
            icon_path,
            text=self.tr(u'Process'),
            callback=self.show_processing,
            parent=self.iface.mainWindow(),
            add_to_menu=True,
            add_to_toolbar=False)

        # Trigger for when the user clicks in the canvas when the panel is open and the cursor is active
        self.point_tool.canvasClicked.connect(self.canvas_click)

    def onClosePlugin(self):
        """Cleanup necessary items here when plugin dockwidget is closed"""

        #print "** CLOSING GeoContextQGISPlugin"

        # disconnects
        self.dockwidget.closingPlugin.disconnect(self.onClosePlugin)

        # remove this statement if dockwidget is to remain
        # for reuse if plugin is reopened
        # Commented next statement since it causes QGIS crashe
        # when closing the docked window:
        # self.dockwidget = None

        self.pluginIsActive = False
        self.canvas.unsetMapTool(self.point_tool)  # Disables the cursor tool

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""

        # UNLOAD GeoContextQGISPlugin
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&GeoContext'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def run(self):
        """Run method that loads and starts the plugin"""

        if not self.pluginIsActive:
            self.pluginIsActive = True

            #print "** STARTING GeoContextQGISPlugin"

            # dockwidget may not exist if:
            #    first run of plugin
            #    removed on close (see self.onClosePlugin method)
            if self.dockwidget == None:
                # Create the dockwidget (after translation) and keep reference
                self.dockwidget = GeoContextQGISPluginDockWidget(self.canvas, self.point_tool)

            # connect to provide cleanup on closing of dockwidget
            self.dockwidget.closingPlugin.connect(self.onClosePlugin)

            # show the dockwidget
            # TODO: fix to allow choice of dock location
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dockwidget)
            self.dockwidget.show()

            self.canvas.setMapTool(self.point_tool)

    def show_options(self):
        dialog = OptionsDialog()
        result = dialog.exec_()

        # See if OK was pressed
        if result:
            dialog.set_url()
            dialog.set_schema()
            dialog.set_auto_clear()
        else:
            pass

    def show_processing(self):
        dialog = ProcessingDialog()
        result = dialog.exec_()

        # See if OK was pressed
        if result:
            error_found = dialog.check_parameters_for_errors()
            if not error_found:
                self.process_points_layer(dialog)
        else:
            pass

    def process_points_layer(self, dialog):
        """
        This method processes a point layer provided by the user.
        The methods takes the point layer provided by the user, and then
        requests the selected registry/key in the processing dialog.
        A new file is created which stores the original attributes with the
        newly requested data. The method will only process the selected features
        if enabled by the user, and the layer can also be loaded into QGIS once
        processing is done.

        :param dialog: Contains the GeoContextQGISPlugin_processing object. It is required
        by this method to retrieve the options selected by the user.
        """

        input_points = dialog.get_input_layer()  # QgsVectorLayer. Input point layer from canvas
        selected_features = dialog.get_selected_option()  # Selected feature will only be taken into account if True
        registry = dialog.get_registry()  # Service, group or collection
        key = dialog.get_key()  # The data which will be requested
        field_name = dialog.get_fieldname().replace(" ", "_")  # Fieldname or suffix. All spaces is replaced with '_'
        output_file = dialog.get_output_points()  # Output point file. Shapefile (shp) or geopackage (gpkg)
        load_output_file = dialog.get_layer_load_option()  # Loads the newly created file if True

        output_file_name = os.path.basename(output_file)
        if selected_features and input_points.selectedFeatureCount() > 0:  # If the selection option is enabled and there is a selection
            if output_file.endswith(".gpkg"):  # Geopackage format
                QgsVectorFileWriter.writeAsVectorFormat(input_points, output_file, 'UTF-8', input_points.crs(), onlySelected=True)
            elif output_file.endswith(".shp"):  # Shapefile format
                QgsVectorFileWriter.writeAsVectorFormat(input_points, output_file, 'UTF-8', input_points.crs(), "ESRI Shapefile", onlySelected=True)  # shp format
            input_new = QgsVectorLayer(output_file, output_file_name)
        else:  # If the only selection option is disabled or there is no features selected
            if output_file.endswith(".gpkg"):  # Geopackage format
                QgsVectorFileWriter.writeAsVectorFormat(input_points, output_file, 'UTF-8', input_points.crs())
            elif output_file.endswith(".shp"):  # Shapefile format
                QgsVectorFileWriter.writeAsVectorFormat(input_points, output_file, 'UTF-8', input_points.crs(), "ESRI Shapefile")  # shp format
            input_new = QgsVectorLayer(output_file, output_file_name)

        # The user selected the 'Service' registry option
        if registry == 'Service':
            input_new.startEditing()
            new_field = QgsField(field_name, QVariant.String)
            input_new.addAttribute(new_field)
            input_new.updateFields()
            input_new.commitChanges()

            input_new.startEditing()
            for input_feat in input_new.getFeatures():  # Processes each of the features contained by the vector file
                new_field_index = input_feat.fieldNameIndex(field_name)

                feat_geom = input_feat.geometry()
                if not feat_geom.isNull():  # If a point does not contain geometry, it is skipped
                    point = feat_geom.asPoint()
                    x = point.x()
                    y = point.y()

                    # The data is requested from the server
                    point_data = self.point_request_dialog(x, y, dialog)
                    point_value_str = str(point_data['value'])

                    input_new.changeAttributeValue(input_feat.id(), new_field_index, point_value_str)
            input_new.commitChanges()
        # The user selected the 'Group' registry option
        elif registry == 'Group':
            # Adds all of the fields to the layer
            for input_feat in input_new.getFeatures():  # Processes each of the features contained by the vector file
                feat_geom = input_feat.geometry()
                if not feat_geom.isNull():  # If a point does not contain geometry, it is skipped
                    point = feat_geom.asPoint()
                    x = point.x()
                    y = point.y()

                    # The data is requested from the server
                    point_data = self.point_request_dialog(x, y, dialog)

                    list_dict_services = point_data["services"]
                    for dict_service in list_dict_services:  # A field is added for each of the group service files
                        key = dict_service['key']
                        coll_field_name = field_name + key

                        # Adds a new field to the attribute table
                        self.create_new_field(input_new, input_feat, coll_field_name)
                break  # Fields only need to be added once for a layer

            # Requests values for all features
            for input_feat in input_new.getFeatures():
                feat_geom = input_feat.geometry()
                if not feat_geom.isNull():  # If a point does not contain geometry, it is skipped
                    point = feat_geom.asPoint()
                    x = point.x()
                    y = point.y()

                    # The data is requested from the server
                    point_data = self.point_request_dialog(x, y, dialog)

                    group_name = point_data['name']
                    list_dict_services = point_data["services"]  # Service files for a group
                    for dict_service in list_dict_services:
                        key = dict_service['key']
                        point_value_str = dict_service['value']
                        coll_field_name = field_name + key

                        input_new.startEditing()
                        field_index = input_feat.fieldNameIndex(coll_field_name)  # Gets the index of the newly added field
                        input_new.startEditing()
                        input_new.changeAttributeValue(input_feat.id(), field_index, point_value_str)
                        input_new.commitChanges()
        # The user selected the 'Collection' registry option
        elif registry == 'Collection':
            # Adds all of the fields to the layer
            for input_feat in input_new.getFeatures():  # Processes each of the features contained by the vector file
                feat_geom = input_feat.geometry()
                if not feat_geom.isNull():  # If a point does not contain geometry, it is skipped
                    point = feat_geom.asPoint()
                    x = point.x()
                    y = point.y()

                    # The data is requested from the server
                    point_data = self.point_request_dialog(x, y, dialog)

                    # Each group contains a list of the 'Service' data associated with the group
                    list_dict_groups = point_data["groups"]
                    for dict_group in list_dict_groups:
                        list_dict_services = dict_group["services"]
                        for dict_service in list_dict_services:  # A field is added for each of the group service files
                            key = dict_service['key']
                            coll_field_name = field_name + key

                            # Adds a new field to the attribute table
                            self.create_new_field(input_new, input_feat, coll_field_name)
                break  # Fields only need to be added once for a layer

            # Requests values for all features
            for input_feat in input_new.getFeatures():
                feat_geom = input_feat.geometry()
                if not feat_geom.isNull():  # If a point does not contain geometry, it is skipped
                    point = feat_geom.asPoint()
                    x = point.x()
                    y = point.y()

                    # The data is requested from the server
                    point_data = self.point_request_dialog(x, y, dialog)

                    collection_name = point_data['name']
                    list_dict_groups = point_data["groups"]  # Each group contains a list of the 'Service' data associated with the group
                    for dict_group in list_dict_groups:
                        group_name = dict_group['name']

                        list_dict_services = dict_group["services"]  # Service files for a group
                        for dict_service in list_dict_services:
                            key = dict_service['key']
                            point_value_str = dict_service['value']
                            coll_field_name = field_name + key

                            input_new.startEditing()
                            field_index = input_feat.fieldNameIndex(coll_field_name)  # Gets the index of the newly added field
                            input_new.startEditing()
                            input_new.changeAttributeValue(input_feat.id(), field_index, point_value_str)
                            input_new.commitChanges()

        # Loads the newly created file into QGIS
        if load_output_file:
            QgsProject.instance().addMapLayer(input_new)

    def point_request_panel(self, x, y):
        """Return the value rettrieved from the ordered dictionary containing the requested data
        from the server. This method is used by the docket widget panel of the plugin.

        This method requests the data from the server for the given point coordinates.

        :param x: Longitude coordinate
        :type x: Numeric

        :param y: Latitude coordinate
        :type y: Numeric

        :returns: The value retrieved for the request for the provided location
        :rtype: Numeric
        """

        settings = QgsSettings()

        api_url = settings.value('geocontext-qgis-plugin/url')  # Base URL. This will/should be set in  the options dialog
        registry = self.dockwidget.cbRegistry.currentText()  # Service, group or collection
        key_name = self.dockwidget.cbKey.currentText()  # Key name, e.g. Elevation

        dict_key = self.dockwidget.find_name_info(key_name, registry)  # Retrieves the request key using the selected key name
        key = dict_key['key']

        # Performs the request
        client = Client()
        url_request = api_url + "query?" + 'registry=' + registry.lower() + '&key=' + key + '&x=' + str(x) + '&y=' + str(y) + '&outformat=json'
        data = client.get(url_request)

        return data['value']

    def point_request_dialog(self, x, y, dialog):
        """Return the value rettrieved from the ordered dictionary containing the requested data
        from the server. This method is used by the processing dialog of the plugin.

        This method requests the data from the server for the given point coordinates.

        :param x: Longitude coordinate
        :type x: Numeric

        :param y: Latitude coordinate
        :type y: Numeric

        :param dialog: Stores the dialog which takes the required parameters as input
        :type dialog: GeoContextQGISPlugin_processing_dialog

        :returns: The data retrieved for the request for the provided location
        :rtype: Ordered dictionary
        """

        settings = QgsSettings()

        api_url = settings.value('geocontext-qgis-plugin/url')  # Base URL. Set in the options dialog
        registry = dialog.get_registry()  # Gets the registry option selected by the user
        key_name = dialog.get_key()  # Gets the key name set by the user

        dict_key = dialog.find_name_info(key_name, registry)  # Retrieved the key ID using the key name
        key = dict_key['key']

        # Performs the request from the server based on the above information
        client = Client()
        url_request = api_url + "query?" + 'registry=' + registry.lower() + '&key=' + key + '&x=' + str(x) + '&y=' + str(y) + '&outformat=json'
        data = client.get(url_request)

        return data

    def canvas_click(self, point_tool):
        """
        This method is called when the plugin docket panel is open and the user clicks
        in the canvas. The method will then request the selected data at the selected location.

        :param dialog: Stores the dialog which takes the required parameters as input
        :type dialog: GeoContextQGISPlugin_processing_dialog
        """

        # The coordinates from the QGIS canvas point tool
        x = point_tool[0]  # Longitude
        y = point_tool[1]  # Latitude

        # Sets the panel values to the above
        self.dockwidget.lineLong.setText(str(x))
        self.dockwidget.lineLat.setText(str(y))

        # Perfors a point data request from the server
        current_key_name = self.dockwidget.cbKey.currentText()
        data = self.point_request_panel(x, y)

        registry = self.dockwidget.cbRegistry.currentText()

        # Service option
        if registry.lower() == 'service':
            settings = QgsSettings()

            # If set in the options dialog, the table will automatically be cleared. This option is only available for Services
            auto_clear_table = settings.value('geocontext-qgis-plugin/auto_clear_table', False, type=bool)
            if auto_clear_table:
                self.dockwidget.clear_results_table()

            self.dockwidget.tblResult.insertRow(0)  # Always add at the top of the table
            self.dockwidget.tblResult.setItem(0, 0, QTableWidgetItem(current_key_name))  # Sets the key in the table
            self.dockwidget.tblResult.setItem(0, 1, QTableWidgetItem(str(data)))  # Sets the description
        elif registry.lower() == "group":  # UPDATE
            list_groups = []
        elif registry.lower() == "collection":  # UPDATE
            list_collections = []

    def create_new_field(self, input_layer, input_feat, field_name):
        """Return index of the field in the input layer attribute table.

        :param input_layer: Layer being processed.
        :type input_layer: QgsVectorLayer

        :param input_feat: Used to retrieve the field index
        :type input_feat: QgsFeature

        :param field_name: Field name which needs to be retrieved
        :type field_name: String

        :returns: The index of the field name, -1 if the attribute table does not contain the field
        :rtype: Integer
        """

        field_index = input_feat.fieldNameIndex(field_name)
        if field_index == -1:  # Checks if the field does not exist in the attribute table
            input_layer.startEditing()
            new_field = QgsField(field_name, QVariant.String)
            input_layer.addAttribute(new_field)
            input_layer.updateFields()
            input_layer.commitChanges()
            field_index = input_feat.fieldNameIndex(field_name)
        return field_index
