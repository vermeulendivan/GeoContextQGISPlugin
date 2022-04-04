# -*- coding: utf-8 -*-
"""
/***************************************************************************
 GeoContextQGISPluginDockWidget
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

import sys
import os
import time
import inspect
import csv

from qgis.PyQt import QtGui, QtWidgets, uic
from qgis.PyQt.QtCore import pyqtSignal, QUrl
from qgis.PyQt.QtWidgets import QTableWidgetItem
from qgis.core import QgsProject, QgsSettings, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsPointXY

from .geocontext_help_dialog import HelpDialog

# Adds the plugin core path to the system path
cur_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(cur_dir)
sys.path.insert(0, parentdir)

from utilities.utilities import (get_request_crs)
from bridge_api.api_abstract import ApiClient
from bridge_api.default import SERVICE, GROUP, COLLECTION, VALUE_JSON, SERVICE_JSON, GROUP_JSON, COLLECTION_JSON

# Core API modules
from requests import exceptions

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'GeoContextQGISPlugin_dockwidget_base.ui'))


class GeoContextQGISPluginDockWidget(QtWidgets.QDockWidget, FORM_CLASS):

    closingPlugin = pyqtSignal()

    def __init__(self, canvas, point_tool, iface, parent=None):
        """Constructor."""
        super(GeoContextQGISPluginDockWidget, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://doc.qt.io/qt-5/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        self.iface = iface  # QGIS interface
        self.canvas = canvas  # QGIS project canvas
        self.point_tool = point_tool  # Canvas point tool - cursor used to selected locations
        self.cursor_active = True  # Sets to True because the point tool is now active

        # Retrieves the schema data from the URL stored using the options dialog
        settings = QgsSettings()
        schema = settings.value('geocontext-qgis-plugin/schema', '', type=str)

        # Attempts to request the schema configuration from the API
        # try:
        #     client = ApiClient()
        #
        #     response = client.get(schema)  # Retrieve the API schema
        #     self.list_context = response.json()
        #
        # except exceptions.ConnectionError:  # Could not connect to the provided URL
        #     error_msg = "Could not connect to " + schema + ". Check if the provided URL is correct. The site may also be down."
        #     self.iface.messageBar().pushCritical("Connection error: ", error_msg)
        #
        #     self.list_context = []
        # except Exception as e:  # Other possible connection issues
        #     error_msg = "Could not connect to " + schema + ". Unknown error: " + str(e)
        #     self.iface.messageBar().pushCritical("Connection error: ", error_msg)
        #
        #     self.list_context = []

        # Services: ONLY TEMP
        self.list_context = [{'key': 'altitude', 'name': 'altitude', 'description': 'N/A'},
                        {'key': 'monthly_max_temperature_december', 'name': 'monthly_max_temperature_december', 'description': 'N/A'},
                        {'key': 'monthly_precipitation_may', 'name': 'monthly_precipitation_may', 'description': 'N/A'}]

        # Groups: ONLY TEMP
        self.list_group = [{'key': 'bioclimatic_variables_group', 'name': 'Bioclimatic layers', 'description': 'N/A'},
                           {'key': 'monthly_precipitation_group', 'name': 'Monthly Precipitation', 'description': 'N/A'},
                           {'key': 'monthly_solar_radiation_group', 'name': 'Monthly Solar Radiation', 'description': 'N/A'},
                           {'key': 'monthly_max_temperature_group', 'name': 'Monthly Maximum Temperature', 'description': 'N/A'}]

        # Collections: ONLY TEMP
        self.list_collection = [{'key': 'global_climate_collection', 'name': 'Global climate collection', 'description': 'N/A'},
                                {'key': 'healthy_rivers_collection', 'name': 'Healthy rivers collection', 'description': 'N/A'},
                                {'key': 'healthy_rivers_spatial_collection', 'name': 'Healthy rivers spatial filters', 'description': 'N/A'},
                                {'key': 'hydrological_regions', 'name': 'Hydrological regions', 'description': 'N/A'},
                                {'key': 'ledet_collection', 'name': 'LEDET collection', 'description': 'N/A'},
                                {'key': 'sa_boundary_collection', 'name': 'South African boundary collection', 'description': 'N/A'},
                                {'key': 'sa_climate_collection', 'name': 'South African climate collection', 'description': 'N/A'},
                                {'key': 'sa_land_cover_land_use_collection', 'name': 'South African land use collection', 'description': 'N/A'},
                                {'key': 'sa_river_ecosystem_collection', 'name': 'South African river collection', 'description': 'N/A'},
                                {'key': 'sedac_collection', 'name': 'Socioeconomic data and application center collection', 'description': 'N/A'}]

        # If the context list is empty, these steps should be skipped
        if len(self.list_context) > 0:
            # Creates a list of the key names and sorts it alphabetically
            list_key_names = []
            for context in self.list_context:
                name = context['name']
                list_key_names.append(name)
            list_key_names = sorted(list_key_names)

            # Adds the keys to the panel
            self.cbKey.addItems(list_key_names)

            # Retrieves panel parameters
            registry = self.cbRegistry.currentText()
            current_name = self.cbKey.currentText()

            # Retrieves the set information and updates the description table with it
            dict_current = self.find_name_info(current_name, registry)
            self.tblDetails.setItem(0, 0, QtWidgets.QTableWidgetItem(dict_current['key']))
            self.tblDetails.setItem(0, 1, QtWidgets.QTableWidgetItem(dict_current['name']))
            self.tblDetails.setItem(0, 2, QtWidgets.QTableWidgetItem(dict_current['description']))
        else:  # Empty geocontext list. This can be a result of the incorrect URL, or the site is down
            error_msg = "The retrieved context list is empty. Check the provided schema configuration URL or whether the site is online."
            self.iface.messageBar().pushCritical("Empty geocontext list error: ", error_msg)

        # UI triggers
        self.cbRegistry.currentTextChanged.connect(self.registry_changed)  # Triggered when the registry changes
        self.cbKey.currentTextChanged.connect(self.key_changed)  # Triggers when the key value changes

        # Button triggers
        self.btnClear.clicked.connect(self.clear_results_table)  # Triggers when the Clear button is clicked
        self.btnFetch.clicked.connect(self.fetch_btn_click)  # Triggers when the Fetch button is pressed
        self.btnCursor.clicked.connect(self.cursor_btn_click)  # Triggers when the Cursor button is pressed
        self.btnHelp.clicked.connect(self.help_btn_click)  # Triggers when the Help button is pressed
        self.btnExport.clicked.connect(self.export_btn_click)  # Triggers when the Export button is pressed

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

    def registry_changed(self):
        """This method is called when the registry option is changed.
        The list in the panel which contains the key names will be updated.
        """

        registry = self.cbRegistry.currentText()  # Gets the registry type
        self.update_key_list(registry)  # Update the key list

    def key_changed(self):
        """This method is called when the key option in the panel window is changed.
        The information in the table which provides a description on the selected
        key will be update.
        """

        # Retrieved registry and newly selected key ID
        registry = self.cbRegistry.currentText()
        key_name = self.cbKey.currentText()

        # If the key name is empty, this step is skipped
        # This happens when the key list is cleared, which then triggers prior to the updating the list
        if len(key_name) > 0:
            dict_current = self.find_name_info(key_name, registry)

            # Updates the table
            self.tblDetails.setItem(0, 0, QtWidgets.QTableWidgetItem(dict_current['key']))
            self.tblDetails.setItem(0, 1, QtWidgets.QTableWidgetItem(dict_current['name']))
            self.tblDetails.setItem(0, 2, QtWidgets.QTableWidgetItem(dict_current['description']))

    def fetch_btn_click(self):
        """This method is called when the Fetch button on the panel window is pressed.
        The location (x and y) currently shown in the panel will be retrieved with no need to click
        in the canvas using the cursor.
        """

        settings = QgsSettings()

        # Gets the longitude and latitude
        x = float(self.lineLong.value())
        y = float(self.lineLat.value())

        # Request starts
        start = time.time()

        # Requests the data
        current_key_name = self.cbKey.currentText()
        data = self.point_request_panel(x, y)

        # Request ends
        end = time.time()
        rounding_factor = settings.value('geocontext-qgis-plugin/dec_places_panel', 3, type=int)
        request_time_ms = round((end - start) * 1000, rounding_factor)
        self.lblRequestTime.setText("Request time (ms): " + str(request_time_ms))

        registry = self.cbRegistry.currentText()  # Registry: Service, group or collection
        # The user has Service selected
        if registry == SERVICE['name']:
            settings = QgsSettings()

            # If set, the table will automatically be cleared. This can be set in the options dialog
            auto_clear_table = settings.value('geocontext-qgis-plugin/auto_clear_table', False, type=bool)
            if auto_clear_table:
                self.clear_results_table()

            # Updates the table
            self.tblResult.insertRow(0)  # Always add at the top of the table
            self.tblResult.setItem(0, 0, QTableWidgetItem(current_key_name))
            self.tblResult.setItem(0, 1, QTableWidgetItem(str(data[VALUE_JSON])))
            self.dockwidget.tblResult.setItem(0, 2, QTableWidgetItem(str(x)))  # Latitude
            self.dockwidget.tblResult.setItem(0, 3, QTableWidgetItem(str(y)))  # Longitude
        # The user has Group selected
        elif registry == GROUP['name']:  # UPDATE
            # group_name = data['name']
            list_dict_services = data[SERVICE_JSON]  # Service files for a group
            for dict_service in list_dict_services:
                # key = dict_service['key']
                point_value = dict_service[VALUE_JSON]
                service_key_name = dict_service['name']

                self.tblResult.insertRow(0)  # Always add at the top of the table
                self.tblResult.setItem(0, 0, QTableWidgetItem(service_key_name))  # Sets the key in the table
                self.tblResult.setItem(0, 1, QTableWidgetItem(str(point_value)))  # Sets the description
                self.dockwidget.tblResult.setItem(0, 2, QTableWidgetItem(str(x)))  # Latitude
                self.dockwidget.tblResult.setItem(0, 3, QTableWidgetItem(str(y)))  # Longitude
        # The user has Collection selected
        elif registry == COLLECTION['name']:
            list_dict_groups = data[GROUP_JSON]  # Each group contains a list of the 'Service' data associated with the group
            for dict_group in list_dict_groups:
                # group_name = dict_group['name']
                list_dict_services = dict_group[SERVICE_JSON]  # Service files for a group
                for dict_service in list_dict_services:
                    # key = dict_service['key']
                    point_value = dict_service[VALUE_JSON]
                    service_key_name = dict_service['name']

                    self.tblResult.insertRow(0)  # Always add at the top of the table
                    self.tblResult.setItem(0, 0, QTableWidgetItem(service_key_name))  # Sets the key in the table
                    self.tblResult.setItem(0, 1, QTableWidgetItem(str(point_value)))  # Sets the description
                    self.dockwidget.tblResult.setItem(0, 2, QTableWidgetItem(str(x)))  # Latitude
                    self.dockwidget.tblResult.setItem(0, 3, QTableWidgetItem(str(y)))  # Longitude

    def cursor_btn_click(self):
        """This method is called when the Cursor button on the panel is clicked.
        The method will either enable or disable the cursor location selection, which
        retrieves the coordinates when the user clicks in the canvas
        """

        if self.cursor_active:
            self.canvas.unsetMapTool(self.point_tool)
            self.cursor_active = False
        else:
            self.canvas.setMapTool(self.point_tool)
            self.cursor_active = True

    def help_btn_click(self):
        self.show_help()

    def export_btn_click(self):
        print("export")

        # CONTINUE HERE. EXPORT TO GPKG ======================================================================================================================

        row_cnt = self.tblResult.rowCount()

        i = 0
        while i < row_cnt:
            key = self.tblResult.item(i, 0).text()
            value = self.tblResult.item(i, 1).text()
            x = self.tblResult.item(i, 2).text()
            y = self.tblResult.item(i, 3).text()

            print(key)
            print(value)
            print(x)
            print(y)

            i = i + 1


    def show_help(self):
        """Opens the help dialog. The dialog displays the html documentation.
        The documentation contains information on the docking panel.
        """

        # Directory of the docking_panel.html file used for the help option
        help_file_dir = '%s/resources/help/build/html/docking_panel.html' % os.path.dirname(os.path.dirname(__file__))
        help_file = 'file:///%s/resources/help/build/html/docking_panel.html' % os.path.dirname(os.path.dirname(__file__))

        # Checks whether the required html document exist
        if os.path.exists(help_file_dir):
            results_dialog = HelpDialog()
            results_dialog.web_view.load(QUrl(help_file))
            results_dialog.exec_()
        # Skips showing the help file because the plugin cannot find it
        else:
            error_msg = "Cannot find the /resources/help/build/html/docking_panel.html file. Cannot open the help dialog."
            self.iface.messageBar().pushCritical("Missing file: ", error_msg)

    def point_request_panel(self, x, y):
        """Return the value retrieved from the ordered dictionary containing the requested data
        from the server. This method is used by the docket widget panel of the plugin.

        This method requests the data from the server for the given point coordinates.

        :param x: Longitude coordinate
        :type x: Float

        :param y: Latitude coordinate
        :type y: Float

        :returns: The data retrieved for the request for the provided location
        :rtype: OrderedDict
        """

        settings = QgsSettings()

        api_url = settings.value('geocontext-qgis-plugin/url')  # Base request URL
        registry = (self.cbRegistry.currentText())  # Registry type
        key_name = self.cbKey.currentText()  # Key name

        # Retrieves the key ID
        dict_key = self.find_name_info(key_name, registry)
        key = dict_key['key']

        # Performs the request
        client = ApiClient()

        url_request = api_url + "query?" + 'registry=' + registry.lower() + '&key=' + key + '&x=' + str(x) + '&y=' + str(y) + '&outformat=json'
        data = client.get(url_request)

        return data.json()

    def clear_results_table(self):
        """Clears the table in the panel. This can be called when the user clicks the
        Clear button, or if the user has automatic clearing enabled.
        """

        row_count = self.tblResult.rowCount()
        while row_count >= 0:
            self.tblResult.removeRow(row_count)
            row_count = row_count - 1

    def find_name_info(self, search_name, registry):
        """The method finds the key ID of a provided key name. It checks each case until
        the correct case is found.

        :param search_name: The search name to retrieve
        :type search_name: str

        :param registry: The registry type selected by the user in the panel
        :type registry: String

        :returns: The key ID of the searched key name; or None if the key could not be found
        :rtype: String
        """

        if registry == SERVICE['name']:
            for context in self.list_context:
                current_name = context['name']
                if current_name == search_name:
                    return context
        elif registry == GROUP['name']:
            for group in self.list_group:
                current_name = group['name']
                if current_name == search_name:
                    return group
        elif registry == COLLECTION['name']:
            for collection in self.list_collection:
                current_name = collection['name']
                if current_name == search_name:
                    return collection

        return None

    def update_key_list(self, registry_type="Service"):
        """This method updates the key name list shown in the panel. It will be called when
        the user changes the registry type
        """

        # Clears the combobox list prior to adding the updated list
        self.cbKey.clear()

        # Service type is the new selection
        if registry_type == "Service":
            settings = QgsSettings()

            # Docs which contains the schema of geocontext. Link can be changed in the options dialog
            schema = settings.value('geocontext-qgis-plugin/schema', '', type=str)

            # Checks whether the provided schema configuration URL is available
            try:
                # Requests the schema
                client = ApiClient()

                response = client.get(schema)  # Retrieve the API schema
                self.list_context = response.json()
            except exceptions.ConnectionError:  # Could not connect to the provided URL
                error_msg = "Could not connect to " + schema + ". Check if the provided URL is correct. The site may also be down."
                self.iface.messageBar().pushCritical("Connection error: ", error_msg)

                self.list_context = []
            except Exception as e:  # Other possible connection issues
                error_msg = "Could not connect to " + schema + ". Unknown error: " + str(e)
                self.iface.messageBar().pushCritical("Connection error: ", error_msg)

                self.list_context = []

            # Checks if the geocontext list contains data
            if len(self.list_context) > 0:
                # Adds the names to a list, and then sorts the list alphabetically
                list_key_names = []
                for context in self.list_context:
                    name = context['name']
                    list_key_names.append(name)
                list_key_names = sorted(list_key_names)

                # Applies the updated list
                self.cbKey.addItems(list_key_names)
            else:  # Empty geocontext list. This can be a result of the incorrect URL, or the site is down
                error_msg = "The retrieved context list is empty. Check the provided schema configuration URL or whether the site is online."
                self.iface.messageBar().pushCritical("Empty geocontext list error: ", error_msg)
        elif registry_type == "Group":
            # Creates a list of the group layers
            list_key_names = []
            for group in self.list_group:
                name = group['name']
                list_key_names.append(name)

            # Updates the keys in the processing dialog
            self.cbKey.addItems(list_key_names)
        elif registry_type == "Collection":
            # Creates a list of the collection layers
            list_key_names = []
            for collection in self.list_collection:
                name = collection['name']
                list_key_names.append(name)

            # Updates the keys in the processing dialog
            self.cbKey.addItems(list_key_names)
