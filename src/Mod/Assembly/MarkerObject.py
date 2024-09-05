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

import math

import FreeCAD as App
import Part

from PySide import QtCore
from PySide.QtCore import QT_TRANSLATE_NOOP

if App.GuiUp:
    import FreeCADGui as Gui

__title__ = "Assembly Marker object"
__author__ = "Ondsel"
__url__ = "https://www.freecad.org"

from pivy import coin
import UtilsAssembly
import Preferences

from SoSwitchMarker import SoSwitchMarker

translate = App.Qt.translate


def get_camera_height(gui_doc):
    activeView = get_active_view(gui_doc)
    if activeView is None:
        return 200

    camera = activeView.getCameraNode()

    # Check if the camera is a perspective camera
    if isinstance(camera, coin.SoPerspectiveCamera):
        return camera.focalDistance.getValue()
    elif isinstance(camera, coin.SoOrthographicCamera):
        return camera.height.getValue()
    else:
        # Default value if camera type is unknown
        return 200


def get_active_view(gui_doc):
    activeView = gui_doc.ActiveView
    if activeView is None:
        # Fall back on current active document.
        activeView = Gui.ActiveDocument.ActiveView
    return activeView


class Marker:
    def __init__(self, marker):
        marker.Proxy = self

        self.createProperties(marker)

        self.setMarkerReference(marker, None)

    def onDocumentRestored(self, marker):
        self.createProperties(marker)

    def createProperties(self, marker):

        if not hasattr(marker, "Reference"):
            marker.addProperty(
                "App::PropertyXLinkSubHidden",
                "Reference",
                "Main",
                QT_TRANSLATE_NOOP("App::Property", "The reference of the marker"),
            )

        if not hasattr(marker, "Placement"):
            marker.addProperty(
                "App::PropertyPlacement",
                "Placement",
                "Main",
                QT_TRANSLATE_NOOP(
                    "App::Property",
                    "This is the local coordinate system within Reference's object that will be used for the marker.",
                ),
            )

        if not hasattr(marker, "Detach"):
            marker.addProperty(
                "App::PropertyBool",
                "Detach",
                "Main",
                QT_TRANSLATE_NOOP(
                    "App::Property",
                    "This prevents Placement from being recalculated, enabling custom positioning of the placement.",
                ),
            )

        if not hasattr(marker, "Offset"):
            marker.addProperty(
                "App::PropertyPlacement",
                "Offset",
                "Main",
                QT_TRANSLATE_NOOP(
                    "App::Property",
                    "This is the attachement offset of the marker.",
                ),
            )

    def dumps(self):
        return None

    def loads(self, state):
        return None

    def onChanged(self, marker, prop):
        """Do something when a property has changed"""
        # App.Console.PrintMessage("Change property: " + str(prop) + "\n")

        # during loading the onchanged may be triggered before full init.
        if App.isRestoring():
            return

        if prop == "Offset":
            if marker.Reference is None:
                return

            self.updateJCSPlacements(marker)

    def execute(self, marker):
        """Do something when doing a recomputation, this method is mandatory"""
        # App.Console.PrintMessage("Recompute Python Box feature\n")
        self.setMarkerReference(marker, marker.Reference)

    def setMarkerReference(self, marker, ref):
        if ref is not None:
            marker.Reference = ref
            marker.Placement = self.findPlacement(marker, marker.Reference)
        else:
            marker.Reference = None
            marker.Placement = App.Placement()

    def updateJCSPlacements(self, marker):
        if not marker.Detach:
            marker.Placement = self.findPlacement(marker, marker.Reference)

    def findPlacement(self, marker, ref):
        plc = UtilsAssembly.findPlacement(ref)

        # We apply the attachement offset.
        plc = plc * marker.Offset

        return plc


class ViewProviderMarker:
    def __init__(self, vobj):
        """Set this object to the proxy object of the actual view provider"""

        vobj.Proxy = self

    def attach(self, vobj):
        """Setup the scene sub-graph of the view provider, this method is mandatory"""
        self.switch_Marker = SoSwitchMarker(vobj)

        self.display_mode = coin.SoType.fromName("SoFCSelection").createInstance()
        self.display_mode.addChild(self.switch_Marker)
        vobj.addDisplayMode(self.display_mode, "Wireframe")

    def updateData(self, marker, prop):
        """If a property of the handled feature has changed we have the chance to handle this here"""
        # marker is the handled feature, prop is the name of the property that has changed
        if prop == "Placement":
            if hasattr(marker, "Reference") and marker.Reference:
                plc = marker.Placement
                self.switch_Marker.whichChild = coin.SO_SWITCH_ALL

                self.switch_Marker.set_marker_placement(plc, marker.Reference)
            else:
                self.switch_Marker.whichChild = coin.SO_SWITCH_NONE

    def showMarker(self, visible, placement=None, ref=None):
        self.switch_Marker.show_marker(visible, placement, ref)

    def setPickableState(self, state: bool):
        """Set JCS selectable or unselectable in 3D view"""
        self.switch_Marker.setPickableState(state)

    def getDisplayModes(self, obj):
        """Return a list of display modes."""
        modes = []
        modes.append("Wireframe")
        return modes

    def getDefaultDisplayMode(self):
        """Return the name of the default display mode. It must be defined in getDisplayModes."""
        return "Wireframe"

    def onChanged(self, vp, prop):
        """Here we can do something when a single property got changed"""
        # App.Console.PrintMessage("Change property: " + str(prop) + "\n")
        if prop == "color_X_axis" or prop == "color_Y_axis" or prop == "color_Z_axis":
            self.switch_Marker.onChanged(vp, prop)

    def getIcon(self):
        return ":/icons/Assembly_CreateMarker.svg"

    def dumps(self):
        """When saving the document this object gets stored using Python's json module.\
                Since we have some un-serializable parts here -- the Coin stuff -- we must define this method\
                to return a tuple of all serializable objects or None."""
        return None

    def loads(self, state):
        """When restoring the serialized object from document we have the chance to set some internals here.\
                Since no data were serialized nothing needs to be done here."""
        return None

    def doubleClicked(self, vobj):
        task = Gui.Control.activeTaskDialog()
        if task:
            task.reject()

        panel = TaskAssemblyCreateMarker(vobj.Object)
        dialog = Gui.Control.showDialog(panel)
        if dialog is not None:
            dialog.setAutoCloseOnTransactionChange(True)
            dialog.setDocumentName(App.ActiveDocument.Name)
        return True

    def canDelete(self, _obj):
        return True


class MarkerSelGate:
    def __init__(self):
        pass

    def allow(self, doc, obj, sub):
        if not sub:
            return False

        if not (obj.isDerivedFrom("Part::Feature") or obj.isDerivedFrom("App::Part")):
            if UtilsAssembly.isLink(obj):
                linked = obj.getLinkedObject()

                if not (linked.isDerivedFrom("Part::Feature") or linked.isDerivedFrom("App::Part")):
                    return False
            else:
                return False

        return True


class TaskAssemblyCreateMarker(QtCore.QObject):
    def __init__(self, markerObj=None):
        super().__init__()

        self.assembly = UtilsAssembly.activeAssembly()

        self.doc = App.ActiveDocument
        self.gui_doc = Gui.getDocument(self.doc)
        self.view = self.gui_doc.activeView()
        if not self.view or not self.doc:
            return

        self.form = Gui.PySideUic.loadUi(":/panels/TaskAssemblyCreateMarker.ui")

        self.form.offsetButton.clicked.connect(self.onOffsetClicked)

        if markerObj:
            Gui.Selection.clearSelection()
            self.creating = False
            self.marker = markerObj
            App.setActiveTransaction("Edit " + markerObj.Label)

            self.updateTaskboxFromMarker()
            self.visibilityBackup = self.marker.Visibility
            self.marker.Visibility = True

        else:
            self.creating = True
            App.setActiveTransaction("Create Marker")

            self.ref = None
            self.preselecting = True

            self.createMarkerObject()
            self.visibilityBackup = False

            self.handleInitialSelection()

        UtilsAssembly.setMarkersAndJointsPickableState(self.doc, False)

        Gui.Selection.addSelectionGate(MarkerSelGate())
        Gui.Selection.addObserver(self, Gui.Selection.ResolveMode.NoResolve)
        Gui.Selection.setSelectionStyle(Gui.Selection.SelectionStyle.GreedySelection)

        self.callbackMove = self.view.addEventCallback("SoLocation2Event", self.moveMouse)
        self.callbackKey = self.view.addEventCallback("SoKeyboardEvent", self.KeyboardEvent)

        self.addition_rejected = False

    def accept(self):
        self.deactivate()

        App.closeActiveTransaction()
        return True

    def reject(self):
        self.deactivate()

        App.closeActiveTransaction(True)
        return True

    def autoClosedOnTransactionChange(self):
        self.reject()

    def deactivate(self):
        Gui.Selection.removeSelectionGate()
        Gui.Selection.removeObserver(self)
        Gui.Selection.setSelectionStyle(Gui.Selection.SelectionStyle.NormalSelection)
        Gui.Selection.clearSelection()
        self.view.removeEventCallback("SoLocation2Event", self.callbackMove)
        self.view.removeEventCallback("SoKeyboardEvent", self.callbackKey)
        UtilsAssembly.setMarkersAndJointsPickableState(self.doc, True)
        if Gui.Control.activeDialog():
            Gui.Control.closeDialog()

        if not self.creating:
            self.marker.Visibility = self.visibilityBackup

    def handleInitialSelection(self):
        selection = Gui.Selection.getSelectionEx("*", 0)
        if len(selection) != 1:
            return

        sel = selection[0]

        if not sel.SubElementNames:
            # no subnames, so its a root assembly itself that is selected.
            Gui.Selection.removeSelection(sel.Object)
            return

        if len(sel.SubElementNames) != 1:
            return

        sub_name = sel.SubElementNames

        self.ref = [sel.Object, [sub_name, sub_name]]
        self.preselecting = False

        self.updateMarker()

    def createMarkerObject(self):
        name = translate("Assembly", "Marker")
        if self.assembly is None:
            self.marker = self.doc.addObject("App::FeaturePython", name)
        else:
            self.marker = self.assembly.newObject("App::FeaturePython", name)

        Marker(self.marker)
        ViewProviderMarker(self.marker.ViewObject)

    def updateOffsetButton(self):
        pos = self.marker.Offset.Base
        self.form.offsetButton.setText(f"({pos.x}, {pos.y}, {pos.z})")

    def onOffsetClicked(self):
        # Open placement editing dialog
        pass

    def updateTaskboxFromMarker(self):
        self.ref = self.marker.Reference
        self.preselecting = False

        Gui.Selection.addSelection(self.ref[0].Document.Name, self.ref[0].Name, self.ref[1][0])

        self.updateMarkerLabels()

    def updateMarker(self):
        self.updateMarkerLabels()

        # Then we pass the new reference to the marker object
        self.marker.Proxy.setMarkerReference(self.marker, self.ref)

    def updateMarkerLabels(self):
        if self.preselecting:
            self.form.attachedLabel.setText(translate("Assembly", "Not attached"))
        else:
            self.form.attachedLabel.setText(translate("Assembly", "Attached to : "))

        if self.ref is None:
            self.form.refLabel.setText("")
        else:
            self.form.refLabel.setText(self.ref[0].Name + "." + self.ref[1][0])

    def moveMouse(self, info):
        if self.ref is None or not self.preselecting:
            return

        cursor_pos = self.view.getCursorPos()
        cursor_info = self.view.getObjectInfo(cursor_pos)

        if not cursor_info:
            if self.ref is not None:
                self.ref = None
                self.updateMarker()
            return

        newPos = App.Vector(cursor_info["x"], cursor_info["y"], cursor_info["z"])
        vertex_name = UtilsAssembly.findElementClosestVertex(self.ref, newPos)

        self.ref = UtilsAssembly.addVertexToReference(self.ref, vertex_name)

        self.updateMarker()

    # 3D view keyboard handler
    def KeyboardEvent(self, info):
        if info["State"] == "UP" and info["Key"] == "ESCAPE":
            self.reject()

        if info["State"] == "UP" and info["Key"] == "RETURN":
            self.accept()

    # selectionObserver stuff
    def addSelection(self, doc_name, obj_name, sub_name, mousePos):
        rootObj = App.getDocument(doc_name).getObject(obj_name)
        sub_name = UtilsAssembly.removeTNPFromSubname(doc_name, obj_name, sub_name)

        ref = [rootObj, [sub_name]]

        # Check if the addition is acceptable (we are not doing this in selection gate to let user move objects)
        if not self.preselecting:
            self.addition_rejected = True
            Gui.Selection.removeSelection(doc_name, obj_name, sub_name)
            return

        # Selection is acceptable so add it

        mousePos = App.Vector(mousePos[0], mousePos[1], mousePos[2])
        vertex_name = UtilsAssembly.findElementClosestVertex(ref, mousePos)

        # add the vertex name to the reference
        self.ref = UtilsAssembly.addVertexToReference(ref, vertex_name)
        self.preselecting = False

        self.updateMarker()

    def removeSelection(self, doc_name, obj_name, sub_name, mousePos=None):
        if self.addition_rejected:
            self.addition_rejected = False
            return

        self.ref = None
        self.preselecting = True

        self.updateMarker()

    def clearSelection(self, doc_name):
        self.preselecting = True
        if self.ref is not None:
            self.ref = None
            self.updateMarker()

    def setPreselection(self, doc_name, obj_name, sub_name):
        if not self.preselecting:
            return

        self.ref = [App.getDocument(doc_name).getObject(obj_name), [sub_name]]
