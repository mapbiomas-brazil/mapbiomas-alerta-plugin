# -*- coding: utf-8 -*-
"""
/***************************************************************************
Name                 : MapBiomas Alert
Description          : MapBiomas Alert
Date                 : April, 2019
copyright            : (C) 2019 by Luiz Motta
email                : motta.luiz@gmail.com

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

__author__ = 'Luiz Motta, Luiz Cortinhas'
__date__ = '2019-04-19'
__copyright__ = '(C) 2019, Luiz Motta, (C) 2022, Luiz Cortinhas'
__revision__ = '$Format:%H$'


import os

from qgis.PyQt.QtCore import QObject, Qt, pyqtSlot
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QToolButton, QMenu

from qgis.core import Qgis, QgsApplication

from .mapbiomasalert import MapBiomasAlert
from .dialog_email_password import DialogEmailPassword, runDialogEmailPassword
from .mapbiomasalert_layer_api import API_MapbiomasAlert

def classFactory(iface):
  return MBAlertPlugin( iface )

class MBAlertPlugin(QObject):
    def __init__(self, iface):
        super().__init__()
        self.iface = iface
        self.name = 'MapBiomas Alert'
        self.mbalert = MapBiomasAlert( self.iface )
        self.api = API_MapbiomasAlert()
        self.localSetting = 'mapbiomas_alert_plugin/{}'
        
        self.toolButton = QToolButton()
        self.toolButton.setMenu( QMenu() )
        self.toolButton.setPopupMode( QToolButton.MenuButtonPopup )
        self.toolBtnAction = iface.addToolBarWidget( self.toolButton )
        self.action, self.actionAlert, self.actionConfig = None, None, None
        self.nameActionAlert = 'MapBiomas Alert'

    def initGui(self):
        # Alert
        about = 'Get alerts from Mapbiomas'
        icon = QIcon( os.path.join( os.path.dirname(__file__), 'mapbiomas_alert.png' ) )
        self.actionAlert = QAction( icon, self.nameActionAlert, self.iface.mainWindow() )
        self.actionAlert.setObjectName( self.nameActionAlert.replace(' ', '') )
        self.actionAlert.setWhatsThis( about )
        self.actionAlert.setStatusTip( about )
        self.actionAlert.triggered.connect( self.runAlert )
        self.iface.addPluginToMenu( f"&{self.nameActionAlert}" , self.actionAlert )
        # Config
        title = 'Config email/password'
        icon = QgsApplication.getThemeIcon('mActionOptions.svg')
        self.actionConfig = QAction( icon, title, self.iface.mainWindow() )
        self.actionConfig.setToolTip( title )
        self.actionConfig.triggered.connect( self.runConfig )
        self.iface.addPluginToMenu( f"&{self.nameActionAlert}" , self.actionConfig )
        # 
        m = self.toolButton.menu()
        m.addAction( self.actionAlert )
        m.addAction( self.actionConfig )
        self.toolButton.setDefaultAction( self.actionAlert )

        self.mbalert.register()

    def unload(self):
        self.iface.removeToolBarIcon( self.actionAlert )
        self.iface.removePluginRasterMenu( self.name, self.actionAlert )
        del self.actionAlert
        del self.mbalert

    @pyqtSlot(bool)
    def runAlert(self, checked):
        if not self.api.tokenOk:
            params = DialogEmailPassword.getConfig( self.localSetting )
            hasRegister = not params['email'] is None
            if hasRegister:
                self.api.setToken( **params )
        self.mbalert.run()

    @pyqtSlot(bool)
    def runConfig(self, checked):
        title = 'MapBiomas Alert Email/Password'
        runDialogEmailPassword( title, self.api, self.localSetting )
