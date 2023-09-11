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

# lazily loaded modules
from lazy_loader.lazy_loader import LazyLoader

Draft = LazyLoader("Draft", globals(), "Draft")

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

#def getPointData():

#class TaskPanelOpPage(PathOpGui.TaskPanelBaseGeometryPage):
class TaskPanelOpPage(PathOpGui.TaskPanelPage):
    """Page controller class for the Probing operation."""

    DataLocation = QtCore.Qt.ItemDataRole.UserRole
    DataReference = QtCore.Qt.ItemDataRole.UserRole + 1

    #def __init__(self, obj, features):
    #    super().__init__(obj, features)
       
    def initPage(self, obj):
        self.editRow = None
        self.panelTitle = 'Probing Locations'

    def getForm(self):
        """getForm() ... returns UI"""
        self.form =  FreeCADGui.PySideUic.loadUi(":/panels/PageOpOMIEdit.ui")
       
        if QtCore.qVersion()[0] == "4":
            self.form.baseList.horizontalHeader().setResizeMode(
                QtGui.QHeaderView.Stretch
            )
        else:
            self.form.baseList.horizontalHeader().setSectionResizeMode(
                QtGui.QHeaderView.Stretch
            )
        
        return self.form

    def getFields(self, obj):
        """getFields(obj) ... transfers values from UI to obj's properties"""
        #print('getFields got activated')
        self.updateToolController(obj, self.form.toolController)
        distance = FreeCAD.Units.Quantity(self.form.sbDistance.text())
        obj.ProbingDistance = distance.Value
        obj.OutputFileName = str(self.form.OutputFileName.text())

    def setFields(self, obj):
        """setFields(obj) ... transfers obj's property values to UI"""
        #print('setFields got activated')
        self.setupToolController(obj, self.form.toolController)
        references = []
        for item in self.job.Operations.Group:
            if not isinstance(item.Proxy, PathOMI.ObjectOMI):
                references.append(item.Name)
        references.append(self.job.Model.Name)
        self.form.cbReferenceGen.addItems(references)
        diameter = obj.ToolController.Tool.Diameter.Value
        probingDistance = max(obj.ProbingDistance, diameter)
        #Is it appropiate to set the obj attributes with this method?
        obj.ProbingDistance = probingDistance
        self.form.sbDistance.setValue(probingDistance)
        self.form.OutputFileName.setText(obj.OutputFileName)
        self.setLocations(obj)
   
    def replaceLocations(self):
        self.form.baseList.blockSignals(True)
        for row in range(self.form.baseList.rowCount()):
            self.form.baseList.removeRow(0)
        for pL in self.obj.ProbingLocations:
            self.obj.Document.removeObject(pL.Name)
        self.form.baseList.blockSignals(False)
        self.genLocations()

    def genLocations(self):
        referenceName = self.form.cbReferenceGen
        n = int(self.form.sbCountGen.text())
        
        FreeCAD.ActiveDocument.recompute()

    def setLocations(self, obj):
        self.form.baseList.blockSignals(True)
        self.form.baseList.clearContents()
        self.form.baseList.setRowCount(0)
        for probingLocation in obj.ProbingLocations:
            ref_label = probingLocation.Reference.Label
            location  = probingLocation.AnchorPoint
            
            self.form.baseList.insertRow(self.form.baseList.rowCount())
            
            item = QtGui.QTableWidgetItem(ref_label)
            item.setData(self.DataReference, ref_label)
            self.form.baseList.setItem(self.form.baseList.rowCount() - 1, 0, item)
            
            coords = (location.x, location.y, location.z)
            for i, coord in enumerate(coords):  
                item = QtGui.QTableWidgetItem("%.3f" % coord)
                item.setData(self.DataLocation, coord)
                self.form.baseList.setItem(self.form.baseList.rowCount() - 1, i+1, item)

        self.form.baseList.resizeColumnToContents(0)
        self.form.baseList.blockSignals(False)
        self.itemActivated()

    def removeLocation(self):
        deletedRows = []
        selected = self.form.baseList.selectedItems()
        for item in selected:
            row = self.form.baseList.row(item)
            if row not in deletedRows:
                deletedRows.append(row)
        for i in sorted(deletedRows)[::-1]:
            self.form.baseList.removeRow(i)
            pL = self.obj.ProbingLocations[i]
            self.obj.Document.removeObject(pL.Name)
        #self.updateLocations()
        FreeCAD.ActiveDocument.recompute()

    def updateLocations(self):
        Path.Log.track()
        locations = []
        for i in range(self.form.baseList.rowCount()):
            x = self.form.baseList.item(i, 1).data(self.DataLocation)
            y = self.form.baseList.item(i, 2).data(self.DataLocation)
            z = self.form.baseList.item(i, 3).data(self.DataLocation)
            location = FreeCAD.Vector(x, y, z)
            self.obj.ProbingLocations[i].Proxy.setAnchorPoint(location)

    def addLocation(self, obj, sel):
        Path.Log.track(sel)
        last_selected = sel[-1]
        if last_selected.PickedPoints:
            point = last_selected.PickedPoints[-1]
            ref = last_selected.Object
            proxy = obj.Proxy
            proxy.addProbingLocation(obj, ref, point)
            FreeCADGui.Selection.clearSelection()
            FreeCAD.ActiveDocument.recompute()
            #self.setDirty()

    def addActivated(self):
        # Quick shorcut before understanding where the 
        # SelectionGate comes from and restore after 
        # task completion
        FreeCADGui.Selection.removeSelectionGate()
       
        self.form.addLocation.setEnabled(False)
        self.form.stopAddition.setEnabled(True)

    def stopAddition(self):
        self.form.addLocation.setEnabled(True)
        self.form.stopAddition.setEnabled(False)

    def itemActivated(self):
        if self.form.baseList.selectedItems():
            self.form.removeLocation.setEnabled(True)
        else:
            self.form.removeLocation.setEnabled(False)

    def activateReplace(self):
        if self.form.baseList.rowCount:
            self.form.pbReplaceGen.setEnabled(True)
        else:
            self.form.pbReplaceGen.setEnabled(False)

    def changeDistance(self):
        distance = FreeCAD.Units.Quantity(self.form.sbDistance.text())
        self.obj.ProbingDistance = distance.Value
        FreeCAD.ActiveDocument.recompute()

    def registerSignalHandlers(self, obj): 
        self.form.baseList.itemSelectionChanged.connect(self.itemActivated)
        #print([item for item in dir(self.form.baseList) if hasattr(getattr(self.form.baseList, item), 'connect')])
        self.form.baseList.itemEntered.connect(self.activateReplace)
        #self.form.baseList.destroyed.connect(self.activateReplace)
        self.form.sbDistance.valueChanged.connect(self.changeDistance)
        self.form.pbAddGen.clicked.connect(self.genLocations)
        self.form.pbReplaceGen.clicked.connect(self.replaceLocations)
        self.form.addLocation.clicked.connect(self.addActivated)
        self.form.stopAddition.clicked.connect(self.stopAddition)
        self.form.removeLocation.clicked.connect(self.removeLocation)
        self.form.SetOutputFileName.clicked.connect(self.SetOutputFileName)

    def getSignalsForUpdate(self, obj):
        """getSignalsForUpdate(obj) ... return list of signals for updating obj"""
        signals = []
        signals.append(self.form.toolController.currentIndexChanged)
        #print(dir(self.form.sbDistance))
        #self.form.sbDistance.valueChanged(self.
        #signals.append(self.form.sbDistance.valueChanged)
        signals.append(self.form.OutputFileName.editingFinished)
        
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

    def updateData(self, obj, prop):
        #print('updateData prop', prop)
        #print(obj.Name)
        if prop in ['ProbingLocations']:
            self.setLocations(obj)
        #    self.addLocation()#self.setFields(obj)

    def updateSelection(self, obj, sel):
        if not self.form.addLocation.isEnabled() and sel:
            #print('pressed addLocation button detected on selection')
            self.addLocation(obj, sel)
        #if self.selectionSupportedAsBaseGeometry(sel, True):
        #    self.form.addBase.setEnabled(True)
        #else:
        #    self.form.addBase.setEnabled(False)

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
