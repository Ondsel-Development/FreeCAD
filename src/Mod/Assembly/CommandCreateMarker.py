# SPDX-License-Identifier: LGPL-2.1-or-later
# /**************************************************************************
#                                                                           *
#    Copyright (c) 2024 Ondsel <development@ondsel.com>                     *
#                                                                           *
#    This file is part of FreeCAD.                                          *
#                                                                           *
#    FreeCAD is free software: you can redistribute it and/or modify it     *
#    under the terms of the GNU Lesser General Public License as            *
#    published by the Free Software Foundation, either version 2.1 of the   *
#    License, or (at your option) any later version.                        *
#                                                                           *
#    FreeCAD is distributed in the hope that it will be useful, but         *
#    WITHOUT ANY WARRANTY; without even the implied warranty of             *
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU       *
#    Lesser General Public License for more details.                        *
#                                                                           *
#    You should have received a copy of the GNU Lesser General Public       *
#    License along with FreeCAD. If not, see                                *
#    <https://www.gnu.org/licenses/>.                                       *
#                                                                           *
# **************************************************************************/

import os
import FreeCAD as App

from PySide.QtCore import QT_TRANSLATE_NOOP

if App.GuiUp:
    import FreeCADGui as Gui
    from PySide import QtCore, QtGui, QtWidgets

import MarkerObject
from MarkerObject import TaskAssemblyCreateMarker
import UtilsAssembly
import Assembly_rc

# translate = App.Qt.translate

__title__ = "Assembly Commands to Create Markers"
__author__ = "Ondsel"
__url__ = "https://www.freecad.org"


class CommandCreateMarker:
    def __init__(self):
        pass

    def GetResources(self):
        return {
            "Pixmap": "Assembly_CreateMarker",
            "MenuText": QT_TRANSLATE_NOOP(
                "Assembly_CreateMarker",
                "Create a Marker",
            ),
            "Accel": "M",
            "ToolTip": "<p>"
            + QT_TRANSLATE_NOOP(
                "Assembly_CreateMarker",
                "A Marker is a local coordinate system that can be attached to a solid. It can be used in joint creation, but it is not mandatory : You can create joints without making individual markers first.",
            )
            + "</p>",
            "CmdType": "ForEdit",
        }

    def IsActive(self):
        return not Gui.Control.activeDialog()

    def Activated(self):
        panel = TaskAssemblyCreateMarker()
        dialog = Gui.Control.showDialog(panel)
        if dialog is not None:
            dialog.setAutoCloseOnTransactionChange(True)
            dialog.setDocumentName(App.ActiveDocument.Name)


if App.GuiUp:
    Gui.addCommand("Assembly_CreateMarker", CommandCreateMarker())
