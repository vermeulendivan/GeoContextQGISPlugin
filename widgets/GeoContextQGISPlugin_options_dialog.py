# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'GeoContextQGISPlugin_options_dialog_base.ui'
#
# Created by: PyQt5 UI code generator 5.15.4
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


import os

from PyQt5.QtWidgets import QDialog
from qgis.PyQt import uic
from qgis.PyQt.QtCore import pyqtSignal, QUrl
from qgis.core import QgsSettings

from .geocontext_help_dialog import HelpDialog

# Import the PyQt and QGIS libraries
# this import required to enable PyQt API v2
# do it before Qt imports

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'GeoContextQGISPlugin_options_dialog_base.ui'))


class OptionsDialog(QDialog, FORM_CLASS):
    def __init__(self, iface, parent=None):
        """Constructor."""
        super(OptionsDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        QDialog.__init__(self, parent)
        self.setupUi(self)

        self.iface = iface

        # Sets the options according what the user has it previously set/saved using the options dialog
        settings = QgsSettings()

        # API configuration
        self.lineUrl.setValue(settings.value('geocontext-qgis-plugin/url', '', type=str))
        self.lineSchema.setValue(settings.value('geocontext-qgis-plugin/schema', '', type=str))

        # Global settings
        self.cbCrs.setCurrentIndex(self.cbCrs.findText(settings.value('geocontext-qgis-plugin/request_crs', "WGS84 (EPSG:4326)", type=str)))

        # Panel settings
        self.checkAutoClear.setChecked(settings.value('geocontext-qgis-plugin/auto_clear_table', False, type=bool))
        self.sldDecPlacesPanel.setValue(settings.value('geocontext-qgis-plugin/dec_places_panel', 3, type=int))
        self.lblDecPlacePanel.setText(str(self.sldDecPlacesPanel.value()))

        # Processing tool settings
        self.sldDecPlacesTool.setValue(settings.value('geocontext-qgis-plugin/dec_places_tool', 3, type=int))
        self.lblDecPlaceTool.setText(str(self.sldDecPlacesTool.value()))

        # Updates the value when the user changes the decimal places
        self.sldDecPlacesPanel.valueChanged.connect(self.dec_places_value_changed_panel)
        self.sldDecPlacesTool.valueChanged.connect(self.dec_places_value_changed_tool)

        # Button clicks
        self.btnHelp.clicked.connect(self.help_btn_click)  # Triggers when the Help button is pressed

    def help_btn_click(self):
        self.show_help()

    def show_help(self):
        """Opens the help dialog. The dialog displays the html documentation.
        The documentation contains information on the options dialog.
        """

        # Directory of the docking_panel.html file used for the help option
        help_file_dir = '%s/resources/help/build/html/options_dialog.html' % os.path.dirname(os.path.dirname(__file__))
        help_file = 'file:///%s/resources/help/build/html/options_dialog.html' % os.path.dirname(os.path.dirname(__file__))

        # Checks whether the required html document exist
        if os.path.exists(help_file_dir):
            results_dialog = HelpDialog()
            results_dialog.web_view.load(QUrl(help_file))
            results_dialog.exec_()
        # Skips showing the help file because the plugin cannot find it
        else:
            error_msg = "Cannot find the /resources/help/build/html/options_dialog.html file. Cannot open the help dialog."
            self.iface.messageBar().pushCritical("Missing file: ", error_msg)

    def dec_places_value_changed_panel(self):
        """This method is called when the user moves the decimal place slider for the panel.
        """

        self.lblDecPlacePanel.setText(str(self.sldDecPlacesPanel.value()))

    def dec_places_value_changed_tool(self):
        """This method is called when the user moves the decimal place slider for the processing tool.
        """

        self.lblDecPlaceTool.setText(str(self.sldDecPlacesTool.value()))

    def set_url(self):
        """Sets the base URL which will be used to request data/values.
        This can be set using this dialog.
        """

        settings = QgsSettings()
        url = self.lineUrl.value()

        settings.setValue('geocontext-qgis-plugin/url', url)

    def set_schema(self):
        """Sets the schema docs provided by the user. This can be set using
        this dialog
        """

        settings = QgsSettings()
        schema = self.lineSchema.value()

        settings.setValue('geocontext-qgis-plugin/schema', schema)

    def set_auto_clear(self):
        """Sets whether the panel table should be cleared when the user clicks in the canvas. This can be set using
        this dialog
        """

        settings = QgsSettings()
        auto_clear = self.checkAutoClear.checkState()

        settings.setValue('geocontext-qgis-plugin/auto_clear_table', auto_clear)

    def set_dec_places_panel(self):
        """Sets the decimal places for the panel value requests. This can be set using
        this dialog
        """

        settings = QgsSettings()
        tick_pos = self.sldDecPlacesPanel.value()

        settings.setValue('geocontext-qgis-plugin/dec_places_panel', tick_pos)

    def set_dec_places_tool(self):
        """Sets the decimal places for the tool value requests. This can be set using
        this dialog
        """

        settings = QgsSettings()
        tick_pos = self.sldDecPlacesTool.value()

        settings.setValue('geocontext-qgis-plugin/dec_places_tool', tick_pos)

    def set_request_coordinate_system(self):
        """Sets the target coordinate system for when requests are performed. This can be set using
        this dialog
        """

        settings = QgsSettings()
        request_crs = self.cbCrs.currentText()

        settings.setValue('geocontext-qgis-plugin/request_crs', request_crs)
