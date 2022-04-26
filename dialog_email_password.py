#!/usr/bin/python3
# # -*- coding: utf-8 -*-
"""
/***************************************************************************
Name                 : DialogEmailPassword
Description          : Class for Dialog with email and password
Date                 : April, 2021
copyright            : (C) 2021 by Luiz Motta
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
from qgis.PyQt.QtCore import (
    QSettings,
    QRegExp, QRegularExpression,
)
from qgis.PyQt.QtWidgets import (
    QApplication,
    QDialog,
    QLabel, QLineEdit,
    QCheckBox, QRadioButton,
    QDialogButtonBox,
    QHBoxLayout, QVBoxLayout
)
from qgis.PyQt.QtGui import QRegularExpressionValidator

from qgis.gui import QgsPasswordLineEdit

from qgis import utils as QgsUtils



class DialogEmailPassword(QDialog):
    def __init__(self, title, hasRegister):
        def setupUI():
            def createLayoutPassword():
                layout = QHBoxLayout()
                # Email
                w = QLabel('Email/Password:', self )
                layout.addWidget( w )
                w = QLineEdit( self )
                self.__dict__['email'] = w
                w.setPlaceholderText('someone@somewhere.com')
                w.setToolTip('Email registered at https://plataforma.alerta.mapbiomas.org/login')
                rx = QRegularExpression( self.emailExpEdit, QRegularExpression.CaseInsensitiveOption )
                w.setValidator( QRegularExpressionValidator( rx ) )
                layout.addWidget( w )
                # Password
                w = QgsPasswordLineEdit( self )
                self.__dict__['password'] = w
                w.setToolTip('Password registered at http://www2.dgi.inpe.br/catalogo/explore')
                w.setEchoMode( QLineEdit.Password )
                layout.addWidget( w )
                # Save
                w = QCheckBox('Register(email/password)', self )
                self.__dict__['register_email_password'] = w
                w.setToolTip('Save in QGIS Config')
                layout.addWidget( w )
                return layout

            def createLayoutRegister():
                layout = QHBoxLayout()
                # Register
                w = QRadioButton('Copy Clipboard register', self )
                self.__dict__['clipboard'] = w
                layout.addWidget( w )
                w = QRadioButton('Clear register', self )
                self.__dict__['clear'] = w
                layout.addWidget( w )
                return layout

            lyt = QVBoxLayout()
            f = createLayoutPassword if not hasRegister else createLayoutRegister
            subLayout = f()
            lyt.addLayout( subLayout )
            # Ok and Cancel
            w = QDialogButtonBox( QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self )
            w.accepted.connect( self.accept )
            w.rejected.connect( self.reject )
            lyt.addWidget( w )
            #
            self.setLayout( lyt )

        super().__init__( QgsUtils.iface.mainWindow() )
        self.setWindowTitle( title )
        self.emailExpEdit = '\\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,4}\\b'
        self.emailExpMath = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
        setupUI()

    def getParams(self):
        params = {}
        for k in ('email', 'password'):
            params[ k ] = self.__dict__[ k ].text()
        return params

    def isValidEmail(self):
        rx = QRegExp( self.emailExpMath )
        return rx.exactMatch( self.email.text() )

    def isCheckedClipboard(self):
        return self.clipboard.isChecked()

    def isCheckedClear(self):
        return self.clear.isChecked()

    def isCheckedSave(self):
        return self.register_email_password.isChecked()

    @staticmethod
    def getConfig(localSetting):
        params = {}
        s = QSettings()
        for k in ('email', 'password'):
            params[ k ] = s.value( localSetting.format( k ), None )
        return params

    @staticmethod
    def setConfig(localSetting, email, password):
        s = QSettings()
        s.setValue( localSetting.format('email'), email )
        s.setValue( localSetting.format('password'), password )

    @staticmethod
    def clearConfig(localSetting):
        s = QSettings()
        s.remove( localSetting.format('email') )
        s.remove( localSetting.format('password') )

    @staticmethod
    def copy2Clipboard(email, password):
        msg = f"{email}/{password}"
        clipboard = QApplication.clipboard()
        clipboard.setText( msg )


def runDialogEmailPassword(title, api, localSetting):
        def checkHasRegister():
            hasRegister = True
            if api.tokenOk:
                return hasRegister
            params = DialogEmailPassword.getConfig( localSetting )
            hasRegister = not params['email'] is None
            if hasRegister:
                api.setToken( **params )
                if not api.tokenOk:
                    DialogEmailPassword.clearConfig()
                    hasRegister = False
            return hasRegister

        msgBar =  QgsUtils.iface.messageBar()
        api.message.connect(  msgBar.pushMessage )
        hasRegister = checkHasRegister()
        dlg = DialogEmailPassword( title, hasRegister )
        result = dlg.exec_()
        if not result:
            return
        # Save clipboard or Clear
        if hasRegister:
            if dlg.isCheckedClipboard():
                dlg.copy2Clipboard( **params )
            if dlg.isCheckedClear():
                dlg.clearConfig( localSetting )
            return
        # Get params and test token
        params = dlg.getParams()
        if not dlg.isValidEmail():
            msgBar.pushMessage( f"Invalid email: {params['email']}", Qgis.Critical )
            return
        params['sendMessage'] = True
        api.setToken( **params )
        if not api.tokenOk:
            return
        if dlg.isCheckedSave():
            del params['sendMessage']
            params['localSetting'] = localSetting
            dlg.setConfig( **params )
