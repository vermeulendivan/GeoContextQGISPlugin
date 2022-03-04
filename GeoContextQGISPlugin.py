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
import os.path
import sys
import os
import time
import inspect

from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, Qt, QVariant, QUrl
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QTableWidgetItem
from qgis.core import (QgsProcessingAlgorithm,
                       QgsApplication,
                       QgsProject,
                       QgsSettings,
                       QgsVectorLayer,
                       QgsField,
                       QgsVectorFileWriter,
                       QgsCoordinateTransformContext,
                       QgsMapLayer,
                       QgsCoordinateTransform,
                       QgsPluginLayerRegistry,
                       QgsLayerTree,
                       QgsMapLayer,
                       Qgis,
                       QgsCoordinateReferenceSystem,
                       QgsCoordinateTransform,
                       QgsPointXY,
                       QgsFeature)
from qgis.gui import QgsMapToolEmitPoint

# Initialize Qt resources from file resources.py
from .resources import *

# Utility functions
from .utilities.utilities import (get_canvas_crs,
                                  get_request_crs,
                                  transform_xy_coordinates,
                                  apply_decimal_places_to_float_panel)

# Import the code for the widgets
from .widgets.GeoContextQGISPlugin_dockwidget import GeoContextQGISPluginDockWidget
from .widgets.GeoContextQGISPlugin_options_dialog import OptionsDialog
from .widgets.geocontext_help_dialog import HelpDialog
from .algorithms.geocontext_point_processing_provider import GeocontextPointProcessingProvider
from .bridge_api.api_abstract import ApiClient
# Importing from local files
# cmd_folder = os.path.split(inspect.getfile(inspect.currentframe()))[0]
# if cmd_folder not in sys.path:
#     sys.path.insert(0, cmd_folder)


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

        self.provider = None

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

        self.message_bar = self.iface.messageBar()

        self.canvas = self.iface.mapCanvas()
        # Enables the cursor tool for selecting locations
        self.point_tool = QgsMapToolEmitPoint(self.canvas)

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
            self.iface.addPluginToMenu(self.menu, action)

        self.actions.append(action)

        return action

    def initProcessing(self):
        """Init Processing provider for QGIS >= 3.8."""
        self.provider = GeocontextPointProcessingProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

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

        self.help_action = self.add_action(
            icon_path,
            text=self.tr('Help', ),
            callback=self.show_help,
            parent=self.iface.mainWindow(),
            add_to_menu=True,
            add_to_toolbar=False)
        self.actions.append(self.help_action)

        self.initProcessing()

        # Trigger for when the user clicks in the canvas when the panel is open
        # and the cursor is active
        self.point_tool.canvasClicked.connect(self.canvas_click)

    def onClosePlugin(self):
        """Cleanup necessary items here when plugin dockwidget is closed"""

        # print "** CLOSING GeoContextQGISPlugin"

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

        QgsApplication.processingRegistry().removeProvider(self.provider)

    def run(self):
        """Run method that loads and starts the plugin"""

        if not self.pluginIsActive:
            self.pluginIsActive = True

            # print "** STARTING GeoContextQGISPlugin"

            # dockwidget may not exist if:
            #    first run of plugin
            #    removed on close (see self.onClosePlugin method)
            if self.dockwidget is None:
                # Create the dockwidget (after translation) and keep reference
                self.dockwidget = GeoContextQGISPluginDockWidget(
                    self.canvas, self.point_tool, self.iface)

            # connect to provide cleanup on closing of dockwidget
            self.dockwidget.closingPlugin.connect(self.onClosePlugin)

            # show the dockwidget
            # TODO: fix to allow choice of dock location
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dockwidget)
            self.dockwidget.show()

            self.canvas.setMapTool(self.point_tool)

    def show_options(self):
        """Opens the options dialog. The user can change/set the settings for the plugin here.
        Settings includes the endpoint URL, schema configuration, decimal places, etc.
        """

        dialog = OptionsDialog(self.iface)
        result = dialog.exec_()

        # The user saved the changes to the settings
        if result:
            dialog.set_url()
            dialog.set_schema()
            dialog.set_auto_clear()
            dialog.set_dec_places_panel()
            dialog.set_dec_places_tool()
            dialog.set_request_coordinate_system()
        # The user closed the dialog without saving
        else:
            pass

    def show_help(self):
        """Opens the help dialog. The dialog displays the html documentation.
        The documentation contains installation instructions, how to use the plugin, etc.
        """

        # Directory of the index.html file used for the help option
        help_file_dir = '%s/resources/help/build/html/index.html' % os.path.dirname(
            __file__)
        help_file = 'file:///%s/resources/help/build/html/index.html' % os.path.dirname(
            __file__)

        # Checks whether the required html document exist
        if os.path.exists(help_file_dir):
            results_dialog = HelpDialog()
            results_dialog.web_view.load(QUrl(help_file))
            results_dialog.exec_()
        # Skips showing the help file because the plugin cannot find it
        else:
            error_msg = "Cannot find the /resources/help/build/html/index.html file. Cannot open the help dialog."
            self.iface.messageBar().pushCritical("Missing file: ", error_msg)

    def point_request_panel(self, x, y, registry, key, api_url):
        """Return the value retrieved from the ordered dictionary containing the requested data
        from the server. This method is used by the docket widget panel of the plugin.

        This method requests the data from the server for the given point coordinates.

        :param x: Longitude coordinate
        :type x: Float

        :param y: Latitude coordinate
        :type y: Float

        :param registry: Service, Group or Collection
        :type registry: String

        :param key: The key which will be used to perform the request
        :type key: String

        :param api_url: Endpoint URL used to perform request
        :type api_url: String

        :returns: The value retrieved for the request for the provided location
        :rtype: OrderedDict
        """

        url_request = api_url + "query?" + 'registry=' + registry.lower() + '&key=' + \
            key + '&x=' + str(x) + '&y=' + str(y) + '&outformat=json'

        # Attempts to perform a data request from the API server
        try:
            # STILL NEED TO ADD TOKEN HERE ====================================
            client = ApiClient()
            data = client.get(url_request)
        except Exception as e:
            error_msg = "Could not request " + \
                url_request + ". Unknown error: " + str(e)
            self.iface.messageBar().pushCritical("Request error: ", error_msg)
            print(str(e))

            data = None  # Nothing to return

        return data

    def canvas_click(self, point_tool):
        """
        This method is called when the plugin docket panel is open and the user clicks
        in the canvas. The method will then request the selected data at the selected location.

        :param point_tool: The QGIS tool object used to retrieve point coordinates from the canvas
        :type point_tool: QgsMapToolEmitPoint
        """

        settings = QgsSettings()
        # Base URL. This will/should be set in  the options dialog
        api_url = settings.value('geocontext-qgis-plugin/url')

        # The coordinates from the QGIS canvas point tool
        x = point_tool[0]  # Longitude
        y = point_tool[1]  # Latitude

        # The coordinate system the QGIS project canvas uses
        canvas_crs = get_canvas_crs(self.iface)
        target_crs = get_request_crs()  # GeoContext request needs to be in WGS84
        if canvas_crs != target_crs:  # If the canvas coordinate system is not WGS84
            # Transforms the canvas point coordinates to WGS84 prior to
            # requesting the data
            x, y = transform_xy_coordinates(x, y, canvas_crs, target_crs)

        # Sets the panel values to the above
        self.dockwidget.lineLong.setText(str(x))
        self.dockwidget.lineLat.setText(str(y))

        # Request starts
        start = time.time()

        # Performs a point data request from the server
        current_key_name = self.dockwidget.cbKey.currentText()
        registry = self.dockwidget.cbRegistry.currentText()  # Service, group or collection

        key_name = self.dockwidget.cbKey.currentText()  # Key name, e.g. Elevation
        # Retrieves the request key using the selected key name
        dict_key = self.dockwidget.find_name_info(key_name, registry)
        key = dict_key['key']

        data = self.point_request_panel(x, y, registry, key, api_url)

        # Checks whether the request has been successful. None indicates
        # unsuccessful
        if data is not None:
            data = data.json()  # Retrieves the json data from the API response

            # Request ends
            end = time.time()
            rounding_factor = settings.value(
                'geocontext-qgis-plugin/dec_places_panel', 3, type=int)
            request_time_ms = round((end - start) * 1000, rounding_factor)
            self.dockwidget.lblRequestTime.setText(
                "Request time (ms): " + str(request_time_ms))

            registry = self.dockwidget.cbRegistry.currentText()
            # Service option
            if registry.lower() == 'service':
                # If set in the options dialog, the table will automatically be
                # cleared
                auto_clear_table = settings.value(
                    'geocontext-qgis-plugin/auto_clear_table', False, type=bool)
                if auto_clear_table:
                    self.dockwidget.clear_results_table()

                point_value_str = data['value']  # Retrieves the value
                rounding_factor = settings.value(
                    'geocontext-qgis-plugin/dec_places_panel', 3, type=int)
                point_value_str = apply_decimal_places_to_float_panel(
                    point_value_str, rounding_factor)

                # Always add at the top of the table
                self.dockwidget.tblResult.insertRow(0)
                self.dockwidget.tblResult.setItem(
                    0, 0, QTableWidgetItem(current_key_name))  # Sets the key in the table
                self.dockwidget.tblResult.setItem(
                    0, 1, QTableWidgetItem(
                        str(point_value_str)))  # Sets the description
            # Group option
            elif registry.lower() == "group":
                # group_name = data['name']
                # Service files for a group
                list_dict_services = data["services"]
                for dict_service in list_dict_services:
                    # key = dict_service['key']
                    point_value_str = dict_service['value']
                    rounding_factor = settings.value(
                        'geocontext-qgis-plugin/dec_places_panel', 3, type=int)
                    point_value_str = apply_decimal_places_to_float_panel(
                        point_value_str, rounding_factor)

                    service_key_name = dict_service['name']

                    # Always add at the top of the table
                    self.dockwidget.tblResult.insertRow(0)
                    self.dockwidget.tblResult.setItem(
                        0, 0, QTableWidgetItem(service_key_name))  # Sets the key in the table
                    self.dockwidget.tblResult.setItem(
                        0, 1, QTableWidgetItem(
                            str(point_value_str)))  # Sets the description
            # Collection option
            elif registry.lower() == "collection":
                # Each group contains a list of the 'Service' data associated
                # with the group
                list_dict_groups = data["groups"]
                for dict_group in list_dict_groups:
                    # group_name = dict_group['name']
                    # Service files for a group
                    list_dict_services = dict_group["services"]
                    for dict_service in list_dict_services:
                        # key = dict_service['key']
                        point_value_str = dict_service['value']
                        rounding_factor = settings.value(
                            'geocontext-qgis-plugin/dec_places_panel', 3, type=int)
                        point_value_str = apply_decimal_places_to_float_panel(
                            point_value_str, rounding_factor)

                        service_key_name = dict_service['name']

                        # Always add at the top of the table
                        self.dockwidget.tblResult.insertRow(0)
                        self.dockwidget.tblResult.setItem(
                            0, 0, QTableWidgetItem(service_key_name))  # Sets the key in the table
                        self.dockwidget.tblResult.setItem(0, 1, QTableWidgetItem(
                            str(point_value_str)))  # Sets the description
        else:  # Request were unsuccessful
            error_msg = "Could not perform data request. Check if the endpoint URL is correct."
            self.iface.messageBar().pushCritical("Request error: ", error_msg)
