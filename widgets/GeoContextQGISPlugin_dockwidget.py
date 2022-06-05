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

from qgis.PyQt import QtGui, QtWidgets, uic
from qgis.PyQt.QtCore import pyqtSignal, QUrl, QVariant
from qgis.PyQt.QtWidgets import QTableWidget, QTableWidgetItem
from qgis.core import (
    QgsProject,
    QgsSettings,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsPointXY,
    QgsVectorLayer,
    QgsField,
    QgsFeature,
    QgsGeometry
)

import httplib2
import requests
from requests import exceptions

from .geocontext_help_dialog import HelpDialog
from .GeoContextQGISPlugin_plot import PlotDialog
from .GeoContextQGISPlugin_table import TableDialog

# Adds the plugin core path to the system path
cur_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(cur_dir)
sys.path.insert(0, parentdir)

from utilities.utilities import (
    get_request_crs,
    create_vector_file,
    check_connection
)
from bridge_api.api_abstract import ApiClient
from bridge_api.default import (
    API_DEFAULT_URL,
    SERVICE,
    GROUP,
    COLLECTION,
    VALUE_JSON,
    SERVICE_JSON,
    GROUP_JSON,
    COLLECTION_JSON,
    TABLE_DATA_TYPE,
    TABLE_VALUE,
    TABLE_LONG,
    TABLE_LAT,
    COORDINATE_SYSTEM,
    SITE_URL
)

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
        self.table_output_file.setFilter("*.gpkg;;*.csv")  # Output format for table exporting set to geopackage

        # This variable will store all the tables
        self.tables = []
        self.new_table()

        available, error_msg = check_connection(SITE_URL)
        if available:
            # Gets the lists of available service, group and collection layers
            self.list_context = self.retrieve_registry_list(API_DEFAULT_URL, SERVICE['key'])  # Service
            self.list_group = self.retrieve_registry_list(API_DEFAULT_URL, GROUP['key'])  # Group
            self.list_collection = self.retrieve_registry_list(API_DEFAULT_URL, COLLECTION['key'])  # Collection
        else:
            # Site is unavailable
            self.iface.messageBar().pushCritical("Connection error: ", error_msg)
            self.list_context = []
            self.list_group = []
            self.list_collection = []

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

            self.tabResults.removeTab(0)  # Removes the already existing tab from the UI
            list_widget = QtWidgets.QListWidget()  # The data is stored here
            self.tabResults.addTab(list_widget, dict_current['key'])  # Adds the new tab using the list widget
            self.cbTab.addItem(dict_current['key'])
        else:  # Empty geocontext list. This can be a result of the incorrect URL, or the site is down
            error_msg = "The retrieved services list is empty."
            self.iface.messageBar().pushCritical("Empty geocontext list error: ", error_msg)

        self.set_connectors()

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

    def set_connectors(self):
        # UI triggers
        self.cbRegistry.currentTextChanged.connect(self.registry_changed)  # Triggered when the registry changes
        self.cbKey.currentTextChanged.connect(self.key_changed)  # Triggers when the key value changes

        self.cbTab.currentIndexChanged.connect(self.tab_combobox_change)
        self.tabResults.currentChanged.connect(self.tab_changed)

        # Button triggers
        self.btnClear.clicked.connect(self.clear_btn_click)
        self.btnFetch.clicked.connect(self.fetch_btn_click)
        self.btnCursor.clicked.connect(self.cursor_btn_click)
        self.btnHelp.clicked.connect(self.help_btn_click)
        self.btnExport.clicked.connect(self.export_btn_click)
        self.btnPlot.clicked.connect(self.plot_btn_click)
        self.btnAdd.clicked.connect(self.add_btn_click)
        self.btnRemove.clicked.connect(self.remove_btn_click)
        self.btnTable.clicked.connect(self.table_btn_click)
        self.btnDelete.clicked.connect(self.delete_btn_click)

    def retrieve_registry_list(self, api_url, registry):
        """Return a list of available layers for the provided registry.

        :param api_url: API URL for doing requests
        :type api_url: str

        :param registry: Registry type: Service, group or collection
        :type registry: str

        :returns: A list of available data in json format
        :rtype: list
        """
        request_url = "{}/registries?registry={}".format(api_url, registry)
        try:
            client = ApiClient()
            response = client.get(request_url)
            list_json = response.json()
        except exceptions.ConnectionError:  # Could not connect to the provided URL
            error_msg = "Could not connect to " + request_url + ". Check if the provided URL is correct. The site may also be down."
            self.iface.messageBar().pushCritical("Connection error: ", error_msg)

            list_json = []
        except Exception as e:  # Other possible connection issues
            error_msg = "Could not connect to " + request_url + ". Unknown error: " + str(e)
            self.iface.messageBar().pushCritical("Connection error: ", error_msg)

            list_json = []

        return list_json

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

            # Set the current tab's text to the currently selected
            row_count = self.tabResults.currentWidget().count()

            if row_count == 0:  # If the tab is empty, rename the tab
                self.update_current_tab_text(dict_current['key'])
            else:  # If the tab already consists of data, create a new one
                self.add_btn_click()

    def tab_changed(self):
        tab_index = self.tabResults.currentIndex()
        cb_index = self.cbTab.currentIndex()

        if tab_index != cb_index:
            self.cbTab.setCurrentIndex(tab_index)
        else:
            # This will happen when the change were a result of the combobox selection
            return

    def tab_combobox_change(self):
        tab_index = self.tabResults.currentIndex()
        cb_index = self.cbTab.currentIndex()

        if tab_index != cb_index:
            self.tabResults.setCurrentIndex(cb_index)
        else:
            # This will happen when the change were a result of a tab selection
            return

    def add_btn_click(self):
        """Adds a new tab to the tabs panel
        """
        # Retrieved registry and newly selected key ID
        registry = self.cbRegistry.currentText()
        key_name = self.cbKey.currentText()

        if key_name != '':
            # Only adds a tab if a key is selected
            # Key list is likely empty when there are no selection
            dict_current = self.find_name_info(key_name, registry)  # Key dict
            key = dict_current['key']

            # Creates a new tab
            list_widget = QtWidgets.QListWidget()
            i = self.tabResults.addTab(list_widget, key)
            self.tabResults.setCurrentIndex(i)  # Selects the newly added tab

            # Adds a new item to the combobox
            self.cbTab.addItem(key)
            self.cbTab.setCurrentIndex(i)

            # Adds a table
            self.new_table()

    def remove_btn_click(self):
        """Remove the selected entry from the table
        """
        qlist_widget = self.tabResults.currentWidget()
        selected_index = qlist_widget.currentRow()
        total = qlist_widget.count()
        selected_index_reverse = total - selected_index - 1  # List is reversed in the table
        tab_index = self.tabResults.currentIndex()

        qlist_widget.takeItem(selected_index)
        selected_table = self.tables[tab_index]
        selected_table.removeRow(selected_index_reverse)

    def delete_btn_click(self):
        """Remove the current tab from the tabs panel
        """
        count = self.tabResults.count()
        if count == 1:  # Keep the last remaining tab, but clears it
            self.clear_results_list()

            self.clear_results_table(0)
        else:  # If there are more than one tab
            index = self.tabResults.currentIndex()
            self.tabResults.removeTab(index)
            self.cbTab.removeItem(index)
            self.delete_table(index)

    def table_btn_click(self):
        # Opens the table dialog
        table_dialog = TableDialog(self.tables.copy(), self.get_tab_names())
        table_dialog.exec_()

    def clear_btn_click(self):
        """This method is called when the clear button is clicked
        """
        self.clear_results_list()  # Clears the list shown in the UI

        index = self.tabResults.currentIndex()
        self.clear_results_table(index)  # Clears the table widget which stores the data

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

        index = self.tabResults.currentIndex()
        table = self.tables[index]  # QTableWidget

        # If set, the table will automatically be cleared. This can be set in the options dialog
        auto_clear_table = settings.value('geocontext-qgis-plugin/auto_clear_table', False, type=bool)
        if auto_clear_table:
            self.clear_results_table(index)

        registry = self.cbRegistry.currentText()  # Registry: Service, group or collection
        # The user has Service selected
        if registry == SERVICE['name']:
            settings = QgsSettings()

            point_value = data[VALUE_JSON]

            # Updates/adds the value to the docking panel table
            qlist_widget = self.tabResults.currentWidget()
            row_index = qlist_widget.count()
            qlist_widget.insertItem(row_index, str(point_value))

            # Updates the table
            table.insertRow(0)  # Always add at the top of the table
            table.setItem(0, 0, QTableWidgetItem(current_key_name))
            table.setItem(0, 1, QTableWidgetItem(str(point_value)))  # Value
            table.setItem(0, 2, QTableWidgetItem(str(x)))  # Latitude
            table.setItem(0, 3, QTableWidgetItem(str(y)))  # Longitude

        # The user has Group selected
        elif registry == GROUP['name']:
            # group_name = data['name']
            list_dict_services = data[SERVICE_JSON]  # Service files for a group
            for dict_service in list_dict_services:
                # key = dict_service['key']
                point_value = dict_service[VALUE_JSON]
                service_key_name = dict_service['name']

                # Updates/adds the value to the docking panel table
                qlist_widget = self.tabResults.currentWidget()
                row_index = qlist_widget.count()
                qlist_widget.insertItem(row_index, str(point_value))

                table.insertRow(0)  # Always add at the top of the table
                table.setItem(0, 0, QTableWidgetItem(service_key_name))  # Sets the key in the table
                table.setItem(0, 1, QTableWidgetItem(str(point_value)))  # Sets the value
                table.setItem(0, 2, QTableWidgetItem(str(x)))  # Latitude
                table.setItem(0, 3, QTableWidgetItem(str(y)))  # Longitude
        # The user has Collection selected
        elif registry == COLLECTION['name']:
            # Each group contains a list of the 'Service' data associated with the group
            list_dict_groups = data[GROUP_JSON]
            for dict_group in list_dict_groups:
                # group_name = dict_group['name']
                list_dict_services = dict_group[SERVICE_JSON]  # Service files for a group
                for dict_service in list_dict_services:
                    # key = dict_service['key']
                    point_value = dict_service[VALUE_JSON]
                    service_key_name = dict_service['name']

                    # Updates/adds the value to the docking panel table
                    qlist_widget = self.tabResults.currentWidget()
                    row_index = qlist_widget.count()
                    qlist_widget.insertItem(row_index, str(point_value))

                    table.insertRow(0)  # Always add at the top of the table
                    table.setItem(0, 0, QTableWidgetItem(service_key_name))  # Sets the key in the table
                    table.setItem(0, 1, QTableWidgetItem(str(point_value)))  # Sets the value
                    table.setItem(0, 2, QTableWidgetItem(str(x)))  # Latitude
                    table.setItem(0, 3, QTableWidgetItem(str(y)))  # Longitude

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

    def plot_btn_click(self):
        self.show_plot()

    def help_btn_click(self):
        """Opens the help dialog.
        """
        self.show_help()

    def export_btn_click(self):
        """Export the contents of the docking widget's table to a
        geopackage (gpkg).
        """
        output_file = self.table_output_file.filePath()  # Output file provided by the user
        output_dir = os.path.dirname(output_file)  # Folder directory of the output

        index = self.tabResults.currentIndex()
        table = self.tables[index]  # QTableWidget

        # Checks whether the table has any contents
        num_rows = table.rowCount()
        if num_rows <= 0:
            # File will not be created
            self.iface.messageBar().pushCritical("Export not performed: ", "Table has no contents!")
            return

        # Checks if the folder path exists
        if os.path.exists(output_dir):
            # Exports the table data
            success, msg = self.export_table(output_file, table)
            if not success:
                # Prints an error message if the output file could not be created
                self.iface.messageBar().pushCritical("Cannot create file: ", msg)
        else:
            # Shows an error message if the folder path does not exist
            if output_dir == "":
                self.iface.messageBar().pushCritical("Output directory does not exist: ",
                                                     "The user has not provided an output file!")
            else:
                self.iface.messageBar().pushCritical("Output directory does not exist: ", output_dir)

    def show_plot(self):
        # Gets the current tab index
        index = self.tabResults.currentIndex()

        # Opens the plot dialog
        plot_dialog = PlotDialog(self.tables, index, self.get_tab_names())
        plot_dialog.exec_()

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

    def new_table(self):
        column_names = [
            TABLE_DATA_TYPE['table'],
            TABLE_VALUE['table'],
            TABLE_LONG['table'],
            TABLE_LAT['table']
        ]
        new_table = QTableWidget()
        new_table.setColumnCount(len(column_names))
        new_table.setHorizontalHeaderLabels(column_names)

        self.tables.append(new_table)

    def delete_table(self, index):
        removed_table = self.tables.pop(index)

        return removed_table

    def update_current_tab_text(self, new_text):
        """Set the current tab's text to the currently selected.
        """
        tab_index = self.tabResults.currentIndex()
        self.tabResults.setTabText(tab_index, new_text)
        self.cbTab.setItemText(tab_index, new_text)

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

        url_request = (
                API_DEFAULT_URL +
                "query?" +
                'registry=' + registry.lower() +
                '&key=' + key +
                '&x=' + str(x) +
                '&y=' + str(y) +
                '&outformat=json'
        )
        data = client.get(url_request)

        return data.json()

    def clear_results_list(self):
        """Clears the table in the panel (qlistwidget). This can be called when the user clicks the
        Clear button, or if the user has automatic clearing enabled.
        """
        qlist_widget = self.tabResults.currentWidget()

        try:
            row_cnt = qlist_widget.count()
        except Exception as e:
            # There are no tabs to delete
            # This will likely happen when the key list is empty
            return

        i = row_cnt - 1
        while i >= 0:
            item_widget = qlist_widget.takeItem(i)
            i = i - 1

        # Retrieved registry and newly selected key ID
        registry = self.cbRegistry.currentText()
        key_name = self.cbKey.currentText()

        # Key dict
        dict_current = self.find_name_info(key_name, registry)

        i = self.tabResults.currentIndex()
        self.tabResults.setTabText(i, dict_current['key'])

    def clear_results_table(self, index):
        """Clears the table widget. This can be called when the user clicks the
        Clear button, or if the user has automatic clearing enabled.
        """
        table_to_clear = self.tables[index]
        row_count = table_to_clear.rowCount()
        while row_count >= 0:
            table_to_clear.removeRow(row_count)
            row_count = row_count - 1

    def export_table(self, output_file, table):
        """Exports the table contents of the docking widget.

        :param output_file: Directory and output file name (gpkg)
        :type output_file: str

        :param table: Pointer to the table from which data will be retrieved
        :type table: QTableWidget

        :returns: success, msg
        :rtype: boolean, string
        """
        new_layer = QgsVectorLayer("Point", "temporary_points", "memory")
        layer_provider = new_layer.dataProvider()

        # Adds the new attributes fields to the layer
        new_layer.startEditing()
        list_attributes = [
            QgsField(TABLE_DATA_TYPE['file'], QVariant.String),
            QgsField(TABLE_VALUE['file'], QVariant.String),
            QgsField(TABLE_LONG['file'], QVariant.Double),
            QgsField(TABLE_LAT['file'], QVariant.Double)]
        layer_provider.addAttributes(list_attributes)
        new_layer.updateFields()
        new_layer.commitChanges()

        row_cnt = table.rowCount()
        # Loops through each of the table entries
        i = table.rowCount() - 1  # Current ID
        while i >= 0:
            key = table.item(i, 0).text()  # Data source
            value = table.item(i, 1).text()  # Value at the point
            x = float(table.item(i, 2).text())  # Longitude
            y = float(table.item(i, 3).text())  # Latitude

            # Creates the new feature and updates its attributes
            new_layer.startEditing()
            new_point = QgsPointXY(x, y)
            new_feat = QgsFeature()
            new_feat.setAttributes([key, value, x, y])
            new_feat.setGeometry(QgsGeometry.fromPointXY(new_point))
            layer_provider.addFeatures([new_feat])
            new_layer.commitChanges()

            i = i - 1

        target_crs = QgsCoordinateReferenceSystem(COORDINATE_SYSTEM)
        success, created_layer, msg = create_vector_file(new_layer, output_file, target_crs)

        return success, msg

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

    def get_tab_names(self):
        # Gets the list of names for the tabs
        total = self.tabResults.count()
        index = 0
        list_tab_names = []
        while total > index:
            list_tab_names.append(self.tabResults.tabText(index))
            index = index + 1

        return list_tab_names

    def update_key_list(self, registry_type="Service"):
        """This method updates the key name list shown in the panel. It will be called when
        the user changes the registry type
        """

        # Clears the combobox list prior to adding the updated list
        self.cbKey.clear()

        # Service type is the new selection
        if registry_type == "Service":
            # Creates a list of the service layers
            list_key_names = []
            for service in self.list_context:
                name = service['name']
                list_key_names.append(name)

            # Updates the keys in the processing dialog
            self.cbKey.addItems(list_key_names)
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
