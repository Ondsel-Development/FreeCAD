# -*- coding: utf-8 -*-
# ***************************************************************************
# *   Copyright (c) 2024 Ondsel <development@ondsel.com>                    *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2 of     *
# *   the License, or (at your option) any later version.                   *
# *   for detail see the LICENCE text file.                                 *
# *                                                                         *
# *   This program is distributed in the hope that it will be useful,       *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU Library General Public License for more details.                  *
# *                                                                         *
# *   You should have received a copy of the GNU Library General Public     *
# *   License along with this program; if not, write to the Free Software   *
# *   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
# *   USA                                                                   *
# *                                                                         *
# ***************************************************************************

import FreeCAD as App
import FreeCADGui
import Part
import os
import datetime
from PySide import QtCore, QtGui


class ReloadableObject:
    state = False

    def __init__(self, obj):
        obj.Proxy = self
        self.Type = "FilePathFeature"
        obj.addProperty(
            "App::PropertyFile", "FilePath", "FilePathFeature", "Path to a file"
        ).FilePath = ""

        obj.addProperty(
            "App::PropertyString",
            "ImportDateTime",
            "FilePathFeature",
            "Last Time the Job was post processed",
        )
        obj.setEditorMode("ImportDateTime", 2)

    def onChanged(self, obj, prop):
        if prop == "FilePath":
            filepath = obj.FilePath
            if filepath.endswith(".stp") or filepath.endswith(".step"):
                self.load_file(obj)

                # update the label
                label = os.path.splitext(os.path.basename(obj.FilePath))[0]
                obj.Label = label

    def execute(self, obj):
        self.state = self.file_changed(obj)

    def file_changed(self, obj):
        if not self.check_file(obj.FilePath):
            return False

        LastModified = os.path.getmtime(obj.FilePath)
        dt_object = datetime.datetime.strptime(
            obj.ImportDateTime, "%a %b %d %H:%M:%S %Y"
        )
        time_string_mtime = dt_object.timestamp()

        return LastModified > time_string_mtime

    def check_file(self, filepath):
        if filepath == "":
            return False

        if not os.path.exists(filepath):
            return False

        if not os.path.isfile(filepath):
            return False

        # check if the path ends with .stp or .step
        if not filepath.endswith(".stp") and not filepath.endswith(".step"):
            return False

        return True

    def load_file(self, obj):

        if not self.check_file(obj.FilePath):
            return

        shape = self.import_step_file(obj)
        obj.Shape = shape
        obj.ImportDateTime = QtCore.QDateTime.currentDateTime().toString()

    def import_step_file(self, obj):
        # Import the STEP file and create a shape
        shape = Part.Shape()
        shape.read(obj.FilePath)
        return shape


class ReloadableObjectViewProvider:
    def __init__(self, vobj):
        vobj.Proxy = self

    def attach(self, vobj):
        self.Object = vobj.Object

    def doubleClicked(self, vobj):
        self.setEditPanel(vobj)

    def setEditPanel(self, vobj, mode=0):
        obj = vobj.Object
        panel = TaskPanel(obj)
        FreeCADGui.Control.showDialog(panel)
        return True

    def getDefaultDisplayMode(self):
        return "Flat Lines"

    def onChanged(self, vp, prop):
        pass

    def getIcon(self):

        current_directory = os.path.dirname(os.path.realpath(__file__))
        if self.Object.Proxy.file_changed(self.Object):
            icon = f"{current_directory}{os.path.sep}reloadable-update.svg"
        else:
            icon = f"{current_directory}{os.path.sep}reloadable.svg"

        return icon

    def updateData(self, obj, prop):
        pass


class TaskPanel:
    def __init__(self, obj):
        self.obj = obj
        current_directory = os.path.dirname(os.path.realpath(__file__))
        self.form = FreeCADGui.PySideUic.loadUi(
            current_directory + os.path.sep + "taskpanel.ui"
        )

        self.form.lineEditFilePath.setText(obj.FilePath)
        self.form.buttonBrowse.clicked.connect(self.open_file_dialog)
        self.form.lineEditFilePath.setText(self.obj.FilePath)

        # set the refresh button state
        self.form.buttonRefresh.setEnabled(self.obj.Proxy.file_changed(self.obj))

        self.form.buttonRefresh.clicked.connect(self.refresh)
        App.ActiveDocument.openTransaction("update Reloadable Object")

    def refresh(self):
        self.obj.Proxy.load_file(self.obj)

    def open_file_dialog(self):
        filename, _ = QtGui.QFileDialog.getOpenFileName(
            None, "Open STEP File", "", "STEP Files (*.step *.stp)"
        )
        if filename:
            self.form.lineEditFilePath.setText(filename)
            self.obj.FilePath = filename

    def accept(self):
        App.ActiveDocument.commitTransaction()
        FreeCADGui.Control.closeDialog()

    def reject(self):
        App.ActiveDocument.abortTransaction()
        FreeCADGui.Control.closeDialog()


class ReloadableObjectCommand:
    def GetResources(self):

        current_directory = os.path.dirname(os.path.realpath(__file__))
        return {
            "MenuText": "Add Reloadable Object",
            "ToolTip": "Create a ReloadableObject and import a STEP file",
            "Pixmap": f"{current_directory}{os.path.sep}reloadable.svg",
        }

    def Activated(self):

        App.ActiveDocument.openTransaction("Add Reloadable Object")

        filename, _ = QtGui.QFileDialog.getOpenFileName(
            None, "Open STEP File", "", "STEP Files (*.step *.stp)"
        )
        if not filename:
            return

        label = os.path.splitext(os.path.basename(filename))[0]

        doc = App.ActiveDocument
        obj = doc.addObject("Part::FeaturePython", f"{label}")

        ReloadableObject(obj)
        ReloadableObjectViewProvider(obj.ViewObject)
        obj.FilePath = filename

        doc.recompute()
        App.ActiveDocument.commitTransaction()

    def IsActive(self):
        return App.ActiveDocument is not None


class Manipulator:
    def modifyMenuBar(self):
        return [
            {
                "insert": "addReloadableObject",
                "menuItem": "Std_Import",
                "before": "Std_Import",
            },
        ]

    def modifyToolBars(self):
        return []

    def modifyContextMenu(self, recipient):
        if recipient == "View":
            return []


if App.GuiUp:
    FreeCADGui.addCommand("addReloadableObject", ReloadableObjectCommand())
    manip = Manipulator()
    FreeCADGui.addWorkbenchManipulator(manip)

    wb = FreeCADGui.activeWorkbench()
    wb.reloadActive()
