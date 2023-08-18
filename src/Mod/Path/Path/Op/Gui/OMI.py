# -*- coding: utf-8 -*-
# ***************************************************************************
# *   Copyright (c) 2017 sliptonic <shopinthewoods@gmail.com>               *
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

import FreeCAD
import FreeCADGui
import Path
import Path.Base.Gui.Util as PathGuiUtil
import Path.Base.Gui.GetPoint as PathGetPoint
import Path.Op.Gui.Base as PathOpGui
import Path.Op.OMI as PathOMI
import PathGui

from PySide.QtCore import QT_TRANSLATE_NOOP
from PySide import QtCore, QtGui
from pivy import coin

__title__ = "OMI Operation UI"
__author__ = "tanahy (Tanausu Hernandez Yanes)"
__url__ = "http://www.freecad.org"
__doc__ = "On Machine Inspection operation page controller and command implementation."


if False:
    Path.Log.setLevel(Path.Log.Level.DEBUG, Path.Log.thisModule())
    Path.Log.trackModule(Path.Log.thisModule())
else:
    Path.Log.setLevel(Path.Log.Level.INFO, Path.Log.thisModule())

translate = FreeCAD.Qt.translate


class TaskPanelOpPage(PathOpGui.TaskPanelPage):
    """Page controller class for the Probing operation."""

    def getForm(self):
        """getForm() ... returns UI"""
        return FreeCADGui.PySideUic.loadUi(":/panels/PageOpOMIEdit.ui")

    def getFields(self, obj):
        """getFields(obj) ... transfers values from UI to obj's properties"""
        self.updateToolController(obj, self.form.toolController)
        #PathGuiUtil.updateInputField(obj, "Xoffset", self.form.Xoffset)
        #PathGuiUtil.updateInputField(obj, "Yoffset", self.form.Yoffset)
        #obj.PointCountX = self.form.PointCountX.value()
        #obj.PointCountY = self.form.PointCountY.value()
        obj.OutputFileName = str(self.form.OutputFileName.text())
        tags = []
        index = self.form.lwTags.currentRow()
        for i in range(0, self.form.lwTags.count()):
            item = self.form.lwTags.item(i)
            enabled = item.checkState() == QtCore.Qt.CheckState.Checked
            x = item.data(self.DataX)
            y = item.data(self.DataY)
            z = item.data(self.DataZ)
            # print("(%.2f, %.2f) i=%d/%s" % (x, y, i, index))
            tags.append((x, y, z, enabled))
        self.tags = tags

    def setFields(self, obj):
        """setFields(obj) ... transfers obj's property values to UI"""
        self.setupToolController(obj, self.form.toolController)
        #self.form.Xoffset.setText(
        #    FreeCAD.Units.Quantity(obj.Xoffset.Value, FreeCAD.Units.Length).UserString
        #)
        #self.form.Yoffset.setText(
        #    FreeCAD.Units.Quantity(obj.Yoffset.Value, FreeCAD.Units.Length).UserString
        #)
        self.form.OutputFileName.setText(obj.OutputFileName)
        #self.form.PointCountX.setValue(obj.PointCountX)
        #self.form.PointCountY.setValue(obj.PointCountY)

    def getSignalsForUpdate(self, obj):
        """getSignalsForUpdate(obj) ... return list of signals for updating obj"""
        signals = []
        signals.append(self.form.toolController.currentIndexChanged)
        #signals.append(self.form.PointCountX.valueChanged)
        #signals.append(self.form.PointCountY.valueChanged)
        signals.append(self.form.OutputFileName.editingFinished)
        #signals.append(self.form.Xoffset.valueChanged)
        #signals.append(self.form.Yoffset.valueChanged)
        self.form.SetOutputFileName.clicked.connect(self.SetOutputFileName)
        return signals

    def SetOutputFileName(self):
        filename = QtGui.QFileDialog.getSaveFileName(
            self.form,
            translate("Path_OMI", "Select Output File"),
            None,
            translate("Path_OMI", "All Files (*.*)"),
        )
        if filename and filename[0]:
            self.obj.OutputFileName = str(filename[0])
            self.setFields(self.obj)

class ProbingPointMarker:
    def __init__(self, point, colors):
        self.point = point
        self.color = colors
        self.sep = coin.SoSeparator()
        self.pos = coin.SoTranslation()
        self.pos.translation = (point.x, point.y, point.z)
        self.sphere = coin.SoSphere()
        self.scale = coin.SoType.fromName("SoShapeScale").createInstance()
        self.scale.setPart("shape", self.sphere)
        self.scale.scaleFactor.setValue(7)
        self.material = coin.SoMaterial()
        self.sep.addChild(self.pos)
        self.sep.addChild(self.material)
        self.sep.addChild(self.scale)
        self.enabled = True
        self.selected = False

    def setSelected(self, select):
        self.selected = select
        self.sphere.radius = 1.5 if select else 1.0
        self.setEnabled(self.enabled)

    def setEnabled(self, enabled):
        self.enabled = enabled
        if enabled:
            self.material.diffuseColor = (
                self.color[0] if not self.selected else self.color[2]
            )
            self.material.transparency = 0.0
        else:
            self.material.diffuseColor = (
                self.color[1] if not self.selected else self.color[2]
            )
            self.material.transparency = 0.6

class ViewProviderProbingPoint(PathOpGui.ViewProvider):
    def __init__(self, vobj, resources):
        super().__init(vobj, resources)

        # initialized later
        self.obj = None
        self.tags = None
        self.switch = None
        self.colors = None

    def setupColors(self):
        def colorForColorValue(val):
            v = [((val >> n) & 0xFF) / 255.0 for n in [24, 16, 8, 0]]
            return coin.SbColor(v[0], v[1], v[2])

        pref = Path.Preferences.preferences()
        #                                     R         G          B          A
        npc = pref.GetUnsigned(
            "DefaultPathMarkerColor", ((85 * 256 + 255) * 256 + 0) * 256 + 255
        )
        hpc = pref.GetUnsigned(
            "DefaultHighlightPathColor", ((255 * 256 + 125) * 256 + 0) * 256 + 255
        )
        dpc = pref.GetUnsigned(
            "DefaultDisabledPathColor", ((205 * 256 + 205) * 256 + 205) * 256 + 154
        )
        self.colors = [
            colorForColorValue(npc),
            colorForColorValue(dpc),
            colorForColorValue(hpc),
        ]

    def attach(self, vobj):
        Path.Log.track()
        self.setupColors()
        self.vobj = vobj
        self.obj = vobj.Object
        self.tags = []
        self.switch = coin.SoSwitch()
        vobj.RootNode.addChild(self.switch)
        self.turnMarkerDisplayOn(False)

        if self.obj and self.obj.Base:
            for i in self.obj.Base.InList:
                if hasattr(i, "Group") and self.obj.Base.Name in [
                    o.Name for o in i.Group
                ]:
                    i.Group = [o for o in i.Group if o.Name != self.obj.Base.Name]
            if self.obj.Base.ViewObject:
                self.obj.Base.ViewObject.Visibility = False
            # if self.debugDisplay() and self.vobj.Debug.ViewObject:
            #    self.vobj.Debug.ViewObject.Visibility = False

    def turnMarkerDisplayOn(self, display):
        sw = coin.SO_SWITCH_ALL if display else coin.SO_SWITCH_NONE
        self.switch.whichChild = sw

    def claimChildren(self):
        Path.Log.track()
        # if self.debugDisplay():
        #    return [self.obj.Base, self.vobj.Debug]
        return [self.obj.Base]

    def onDelete(self, arg1=None, arg2=None):
        """this makes sure that the base operation is added back to the job and visible"""
        Path.Log.track()
        if self.obj.Base and self.obj.Base.ViewObject:
            self.obj.Base.ViewObject.Visibility = True
        job = PathUtils.findParentJob(self.obj)
        if arg1.Object and arg1.Object.Base and job:
            job.Proxy.addOperation(arg1.Object.Base, arg1.Object)
            arg1.Object.Base = None
        # if self.debugDisplay():
        #    self.vobj.Debug.removeObjectsFromDocument()
        #    self.vobj.Debug.Document.removeObject(self.vobj.Debug.Name)
        #    self.vobj.Debug = None
        return True

    def updatePositions(self, positions, disabled):
        for tag in self.tags:
            self.switch.removeChild(tag.sep)
        tags = []
        for i, p in enumerate(positions):
            tag = ProbePointMarker(p, self.colors)
            tag.setEnabled(not i in disabled)
            tags.append(tag)
            self.switch.addChild(tag.sep)
        self.tags = tags

    def updateData(self, obj, propName):
        Path.Log.track(propName)
        if "Disabled" == propName:
            self.updatePositions(obj.Positions, obj.Disabled)

    def onModelChanged(self):
        Path.Log.track()
        # if self.debugDisplay():
        #    self.vobj.Debug.removeObjectsFromDocument()
        #    for solid in self.obj.Proxy.solids:
        #        tag = self.obj.Document.addObject('Part::Feature', 'tag')
        #        tag.Shape = solid
        #        if tag.ViewObject and self.vobj.Debug.ViewObject:
        #            tag.ViewObject.Visibility = self.vobj.Debug.ViewObject.Visibility
        #            tag.ViewObject.Transparency = 80
        #        self.vobj.Debug.addObject(tag)
        #    tag.purgeTouched()

    def setEdit(self, vobj, mode=0):
        panel = TaskPanelOpPage(vobj.Object, self)
        self.setupTaskPanel(panel)
        return True

    def unsetEdit(self, vobj, mode):
        if hasattr(self, "panel") and self.panel:
            self.panel.abort()

    def setupTaskPanel(self, panel):
        self.panel = panel
        FreeCADGui.Control.closeDialog()
        FreeCADGui.Control.showDialog(panel)
        panel.setupUi()
        FreeCADGui.Selection.addSelectionGate(self)
        FreeCADGui.Selection.addObserver(self)

    def clearTaskPanel(self):
        self.panel = None
        FreeCADGui.Selection.removeSelectionGate()
        FreeCADGui.Selection.removeObserver(self)
        self.turnMarkerDisplayOn(False)

    # SelectionObserver interface

    def selectTag(self, index):
        Path.Log.track(index)
        for i, tag in enumerate(self.tags):
            tag.setSelected(i == index)

    def tagAtPoint(self, point):
        for i, tag in enumerate(self.tags):
            if Path.Geom.pointsCoincide(
                point, tag.point, tag.sphere.radius.getValue() * 1.3
            ):
                return i
        return -1

    def allow(self, doc, obj, sub):
        if obj == self.obj:
            return True
        return False

    def addSelection(self, doc, obj, sub, point):
        Path.Log.track(doc, obj, sub, point)
        if self.panel:
            i = self.tagAtPoint(point, sub is None)
            self.panel.selectTagWithId(i)
        FreeCADGui.updateGui()



Command = PathOpGui.SetupOperation(
    "OMI",
    PathOMI.Create,
    TaskPanelOpPage,
    "Path_OMI",
    QtCore.QT_TRANSLATE_NOOP("Path_OMI", "On Machine Inspection"),
    QtCore.QT_TRANSLATE_NOOP("Path_OMI", "Create a Probing Grid from a job path or paths"),
    PathOMI.SetupProperties,
)

FreeCAD.Console.PrintLog("Loading PathOMIGui... done\n")
