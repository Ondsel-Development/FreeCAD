# SPDX-License-Identifier: LGPL-2.1-or-later
# /**************************************************************************
#                                                                           *
#    Copyright (c) 2023 Ondsel <development@ondsel.com>                     *
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

import re
import os
import FreeCAD as App

from pivy import coin
from Part import LineSegment, Compound

from PySide.QtCore import QT_TRANSLATE_NOOP

if App.GuiUp:
    import FreeCADGui as Gui
    from PySide import QtCore, QtGui, QtWidgets
    from PySide.QtWidgets import QPushButton, QMenu

import UtilsAssembly
import Preferences

try:
    import sys,os,traceback,inspect,time
    from datetime import datetime
except ImportError:
    App.Console.PrintError("\n\nSeems the python standard libs are not installed, bailing out!\n\n")
    raise

def trace():
    print("Trace Begin")
    lines = traceback.format_stack()
    for i in range(0, len(lines) - 1):
        print(lines[i].strip().split('\n', 1)[0])

# translate = App.Qt.translate

__title__ = "Assembly Command Create Simulation"
__author__ = "Ondsel"
__url__ = "https://www.freecad.org"


class CommandCreateSimulation:
    def __init__(self):
        pass

    def GetResources(self):
        return {
            "Pixmap": "Assembly_CreateSimulation",
            "MenuText": QT_TRANSLATE_NOOP("Assembly_CreateSimulation", "Create Simulation"),
            "Accel": "S",
            "ToolTip": "<p>"
            + QT_TRANSLATE_NOOP(
                "Assembly_CreateSimulation",
                "Create a simulation of the current assembly.",
            )
            + "</p>",
            "CmdType": "ForEdit",
        }

    def IsActive(self):
        return (
            UtilsAssembly.isAssemblyCommandActive()
            and UtilsAssembly.assembly_has_at_least_n_parts(2)
        )

    def Activated(self):
        assembly = UtilsAssembly.activeAssembly()
        if not assembly:
            return

        self.panel = TaskAssemblyCreateSimulation()
        Gui.Control.showDialog(self.panel)


######### Simulation Object ###########
class Simulation:
    def __init__(self, feaPy):

        feaPy.Proxy = self

        if not hasattr(feaPy, "aTimeStart"):
            feaPy.addProperty(
                "App::PropertyTime",
                "aTimeStart",
                "Simulation",
                QT_TRANSLATE_NOOP(
                    "App::Property",
                    "Simulation start time.",
                ),
            )

        if not hasattr(feaPy, "bTimeEnd"):
            feaPy.addProperty(
                "App::PropertyTime",
                "bTimeEnd",
                "Simulation",
                QT_TRANSLATE_NOOP(
                    "App::Property",
                    "Simulation end time.",
                ),
            )

        if not hasattr(feaPy, "cTimeStepOutput"):
            feaPy.addProperty(
                "App::PropertyTime",
                "cTimeStepOutput",
                "Simulation",
                QT_TRANSLATE_NOOP(
                    "App::Property",
                    "Simulation time step for output.",
                ),
            )

        if not hasattr(feaPy, "dTimeStepMinimum"):
            feaPy.addProperty(
                "App::PropertyTime",
                "dTimeStepMinimum",
                "Simulation",
                QT_TRANSLATE_NOOP(
                    "App::Property",
                    "Minimum integration time step allowed.",
                ),
            )

        if not hasattr(feaPy, "eTimeStepMaximum"):
            feaPy.addProperty(
                "App::PropertyTime",
                "eTimeStepMaximum",
                "Simulation",
                QT_TRANSLATE_NOOP(
                    "App::Property",
                    "Maximum integration time step allowed.",
                ),
            )

        if not hasattr(feaPy, "fGlobalErrorTolerance"):
            feaPy.addProperty(
                "App::PropertyFloat",
                "fGlobalErrorTolerance",
                "Simulation",
                QT_TRANSLATE_NOOP(
                    "App::Property",
                    "Integration global error tolerance.",
                ),
            )

        if not hasattr(feaPy, "gCurrentFrame"):
            feaPy.addProperty(
                "App::PropertyInteger",
                "gCurrentFrame",
                "Simulation",
                QT_TRANSLATE_NOOP(
                    "App::Property",
                    "Current Frame Number.",
                ),
            )

        if not hasattr(feaPy, "hStartFrame"):
            feaPy.addProperty(
                "App::PropertyInteger",
                "hStartFrame",
                "Simulation",
                QT_TRANSLATE_NOOP(
                    "App::Property",
                    "Start Frame Number.",
                ),
            )
            
        if not hasattr(feaPy, "iEndFrame"):
            feaPy.addProperty(
                "App::PropertyInteger",
                "iEndFrame",
                "Simulation",
                QT_TRANSLATE_NOOP(
                    "App::Property",
                    "End Frame Number.",
                ),
            )
            
        if not hasattr(feaPy, "jFramesPerSecond"):
            feaPy.addProperty(
                "App::PropertyInteger",
                "jFramesPerSecond",
                "Simulation",
                QT_TRANSLATE_NOOP(
                    "App::Property",
                    "Frames Per Second.",
                ),
            )

        feaPy.aTimeStart = 0.0
        feaPy.bTimeEnd = 1.0
        feaPy.cTimeStepOutput = 1.0e-2
        feaPy.dTimeStepMinimum = 1.0e-9
        feaPy.eTimeStepMaximum = 1.0
        feaPy.fGlobalErrorTolerance = 1.0e-6
        feaPy.gCurrentFrame = 0
        feaPy.hStartFrame = 1
        feaPy.iEndFrame = 100
        feaPy.jFramesPerSecond = 30
            
    def dumps(self):
        return None

    def loads(self, state):
        return None

    def onChanged(self, feaPy, prop):
        assert feaPy.isDerivedFrom("App::FeaturePython") , "Type error"
        pass

    def execute(self, feaPy):
        """Do something when doing a recomputation, this method is mandatory"""
        assert feaPy.isDerivedFrom("App::FeaturePython") , "Type error"
        # App.Console.PrintMessage("Recompute Python Box feature\n")
        pass

    def getAssembly(self, feaPy):
        assert feaPy.isDerivedFrom("App::FeaturePython") , "Type error"
        for obj in feaPy.InList:
            if obj.isDerivedFrom("Assembly::AssemblyObject"):
                return obj
        return None


class ViewProviderSimulation:
    def __init__(self, vpDoc):
        assert isinstance(vpDoc, Gui.ViewProviderDocumentObject) , "Type error"
        vpDoc.Proxy = self
        self.Object = vpDoc.Object
        assert self.Object.isDerivedFrom("App::FeaturePython") , "Type error"
        self.setProperties(vpDoc)

    def setProperties(self,vpDoc):
        """Give the component view provider its component view provider specific properties.

        You can learn more about properties here:
        https://wiki.freecad.org/property
        """

        assert isinstance(vpDoc, Gui.ViewProviderDocumentObject) , "Type error"
        pl = vpDoc.PropertiesList
        if not "Decimals" in pl:
            vpDoc.addProperty("App::PropertyInteger",       "Decimals",    "Space",QT_TRANSLATE_NOOP("App::Property","The number of decimals to use for calculated texts"))
            vpDoc.Decimals = 9

    def attach(self, vpDoc):
        """Setup the scene sub-graph of the view provider, this method is mandatory"""
        assert isinstance(vpDoc, Gui.ViewProviderDocumentObject) , "Type error"
        self.app_obj = vpDoc.Object

        self.display_mode = coin.SoType.fromName("SoFCSelection").createInstance()

        vpDoc.addDisplayMode(self.display_mode, "Wireframe")

    def updateData(self, feaPy, prop):
        """If a property of the handled feature has changed we have the chance to handle this here"""
        assert feaPy.isDerivedFrom("App::FeaturePython") , "Type error"
        pass

    def getDisplayModes(self, vpDoc):
        """Return a list of display modes."""
        assert isinstance(vpDoc, Gui.ViewProviderDocumentObject) , "Type error"
        return ["Wireframe"]

    def getDefaultDisplayMode(self):
        """Return the name of the default display mode. It must be defined in getDisplayModes."""
        return "Wireframe"

    def onChanged(self, vpDoc, prop):
        """Here we can do something when a single property got changed"""
        assert isinstance(vpDoc, Gui.ViewProviderDocumentObject) , "Type error"
        # App.Console.PrintMessage("Change property: " + str(prop) + "\n")
        pass

    def getIcon(self):
        return ":/icons/Assembly_CreateSimulation.svg"

    def dumps(self):
        """When saving the document this object gets stored using Python's json module.\
                Since we have some un-serializable parts here -- the Coin stuff -- we must define this method\
                to return a tuple of all serializable objects or None."""
        return None

    def loads(self, state):
        """When restoring the serialized object from document we have the chance to set some internals here.\
                Since no data were serialized nothing needs to be done here."""
        return None

    def doubleClicked(self, vpDoc):
        assert isinstance(vpDoc, Gui.ViewProviderDocumentObject) , "Type error"
        task = Gui.Control.activeTaskDialog()
        if task:
            task.reject()

        assembly = vpDoc.Object.Proxy.getAssembly(vpDoc.Object)

        if assembly is None:
            return False

        if UtilsAssembly.activeAssembly() != assembly:
            Gui.ActiveDocument.setEdit(assembly)

        panel = TaskAssemblyCreateSimulation(vpDoc.Object)
        Gui.Control.showDialog(panel)

        return True

    def onDelete(self, vpDoc, subelements):
        assert isinstance(vpDoc, Gui.ViewProviderDocumentObject) , "Type error"
        for obj in self.claimChildren():
            obj.Document.removeObject(obj.Name)
        return True

class SimulationSelGate:
    def __init__(self, assembly, simObj):
        self.assembly = assembly
        self.simFeaturePy = simObj

    def allow(self, doc, obj, sub):
        if (obj.Name == self.assembly.Name and sub) or self.assembly.hasObject(obj, True):
            # Objects within the assembly.
            return True

        if obj in self.simFeaturePy.Moves:
            # Enable selection of steps object
            return True

        return False


######### Create Simulation Task ###########
class TaskAssemblyCreateSimulation(QtCore.QObject):
    def __init__(self, simFeaturePy=None):
        super().__init__()
        
        global activeTask
        activeTask = self

        self.assembly = UtilsAssembly.activeAssembly()
        if not self.assembly:
            self.assembly = UtilsAssembly.activePart()
            self.activeType = "Part"
        else:
            self.activeType = "Assembly"

        self.doc = self.assembly.Document
        self.gui_doc = Gui.getDocument(self.doc)

        self.view = self.gui_doc.activeView()

        if not self.assembly or not self.view or not self.doc:
            return

        if self.activeType == "Assembly":
            self.assembly.ViewObject.EnableMovement = False
            
        self.runKinematicsTimer = QtCore.QTimer()
        self.runKinematicsTimer.setSingleShot(True)
        self.runKinematicsTimer.timeout.connect(self.displayLastFrame)
            
        self.animationTimer = QtCore.QTimer()
        self.animationTimer.setInterval(50) # ms
        self.animationTimer.timeout.connect(self.playAnimation)


        self.form = Gui.PySideUic.loadUi(":/panels/TaskAssemblyCreateSimulation.ui")
        self.form.TimeStartSpinBox.valueChanged.connect(self.onTimeStartChanged)
        self.form.TimeEndSpinBox.valueChanged.connect(self.onTimeEndChanged)
        self.form.TimeStepOutputSpinBox.valueChanged.connect(self.onTimeStepOutputChanged)
        self.form.TimeStepMinimumSpinBox.valueChanged.connect(self.onTimeStepMinimumChanged)
        self.form.TimeStepMaximumSpinBox.valueChanged.connect(self.onTimeStepMaximumChanged)
        self.form.GlobalErrorToleranceSpinBox.valueChanged.connect(self.onGlobalErrorToleranceChanged)
        self.form.InputStateRadioButton.toggled.connect(self.on_radio_button_toggled)
        self.form.InitialAssembledStateRadioButton.toggled.connect(self.on_radio_button_toggled)
        self.form.CurrentStateRadioButton.toggled.connect(self.on_radio_button_toggled)
        self.form.RunKinematicsButton.clicked.connect(self.runKinematics)
        self.form.CurrentFrameSpinBox.valueChanged.connect(self.onCurrentFrameChanged)
        self.form.StartFrameSpinBox.valueChanged.connect(self.onStartFrameChanged)
        self.form.EndFrameSpinBox.valueChanged.connect(self.onEndFrameChanged)
        self.form.FramesPerSecondSpinBox.valueChanged.connect(self.onFramesPerSecondChanged)
        self.form.PlayBackwardButton.clicked.connect(self.animationTimerStartBackward)
        self.form.PlayForwardButton.clicked.connect(self.animationTimerStartForward)
        self.form.StepBackwardButton.clicked.connect(self.stepBackward)
        self.form.StepForwardButton.clicked.connect(self.stepForward)
        
        if simFeaturePy:
            Gui.Selection.clearSelection()
            self.creating = False
            self.simFeaturePy = simFeaturePy
            self.simFeaturePyName = simFeaturePy.Label
            App.setActiveTransaction("Edit " + self.simFeaturePyName + " Simulation")
            self.updateTaskboxFromSimulation()
            self.visibilityBackup = self.simFeaturePy.Visibility
            self.simFeaturePy.Visibility = True
        else:
            self.creating = True
            App.setActiveTransaction("Create Simulation")

            self.current_selection = []
            self.preselection_dict = None

            self.createSimulationObject()
            self.updateTaskboxFromSimulation()
            self.visibilityBackup = False

        self.adaptUi()
        
        self.currentFrm = 1
        self.startFrm = 1
        self.endFrm = 100
        self.fps = 30
        self.deltaTime = 1.0 / self.fps
        self.startTime = time.time()
        self.index = 0
        # Gui.Selection.addSelectionGate(
        #     SimulationSelGate(self.assembly, self.simFeaturePy), Gui.Selection.ResolveMode.NoResolve
        # )
        # Gui.Selection.addObserver(self, Gui.Selection.ResolveMode.NoResolve)
        # Gui.Selection.setSelectionStyle(Gui.Selection.SelectionStyle.GreedySelection)

        # self.form.featureList.installEventFilter(self)
    
    def adaptUi(self):
        self.form.TimeStartLabel.show()
        self.form.TimeStartSpinBox.show()
        self.form.TimeEndLabel.show()
        self.form.TimeEndSpinBox.show()
        self.form.TimeStepOutputLabel.show()
        self.form.TimeStepOutputSpinBox.show()
        self.form.TimeStepMinimumLabel.show()
        self.form.TimeStepMinimumSpinBox.show()
        self.form.TimeStepMaximumLabel.show()
        self.form.TimeStepMaximumSpinBox.show()
        self.form.GlobalErrorToleranceLabel.show()
        self.form.GlobalErrorToleranceSpinBox.show()
        self.form.InputStateRadioButton.show()
        self.form.InitialAssembledStateRadioButton.show()
        self.form.CurrentStateRadioButton.show()
        self.form.RunKinematicsButton.show()
        self.form.CurrentFrameLabel.show()
        self.form.CurrentFrameSpinBox.show()
        self.form.StartFrameLabel.show()
        self.form.StartFrameSpinBox.show()
        self.form.EndFrameLabel.show()
        self.form.EndFrameSpinBox.show()
        self.form.FramesPerSecondLabel.show()
        self.form.FramesPerSecondSpinBox.show()
        self.form.PlayBackwardButton.show()
        self.form.PlayForwardButton.show()
        self.form.StepBackwardButton.show()
        self.form.StepForwardButton.show()

    def accept(self):
        self.deactivate()
        App.closeActiveTransaction()
        return True

    def reject(self):
        self.deactivate()
        App.closeActiveTransaction(True)
        return True

    def deactivate(self):
        pref = Preferences.preferences()

        view = Gui.activeDocument().activeView()

        Gui.Selection.removeSelectionGate()
        Gui.Selection.removeObserver(self)
        Gui.Selection.clearSelection()

        if Gui.Control.activeDialog():
            Gui.Control.closeDialog()

    def onTimeStartChanged(self, quantity):
        self.simFeaturePy.aTimeStart = self.form.TimeStartSpinBox.value()

    def onTimeEndChanged(self, quantity):
        self.simFeaturePy.bTimeEnd = self.form.TimeEndSpinBox.value()

    def onTimeStepOutputChanged(self, quantity):
        self.simFeaturePy.cTimeStepOutput = self.form.TimeStepOutputSpinBox.value()

    def onTimeStepMinimumChanged(self, quantity):
        self.simFeaturePy.dTimeStepMinimum = self.form.TimeStepMinimumSpinBox.value()

    def onTimeStepMaximumChanged(self, quantity):
        self.simFeaturePy.eTimeStepMaximum = self.form.TimeStepMaximumSpinBox.value()

    def onGlobalErrorToleranceChanged(self, quantity):
        self.simFeaturePy.fGlobalErrorTolerance = self.form.GlobalErrorToleranceSpinBox.value()

    def onItemClicked(self, item):
        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(self.simFeaturePy.Document.Name, item.text(), "")
        # we give back the focus to the item as addSelection gave the focus to the 3dview
        self.form.stepList.setCurrentItem(item)

    def endSelectionMode(self):
        self.selectingFeature = False
        Gui.Selection.setSelectionStyle(Gui.Selection.SelectionStyle.NormalSelection)

    def createSimulationObject(self):
        sim_group = UtilsAssembly.getSimulationGroup(self.assembly)
        self.simFeaturePy = sim_group.newObject("App::FeaturePython", "Simulation")
        Simulation(self.simFeaturePy)
        ViewProviderSimulation(self.simFeaturePy.ViewObject)

    def clickMouse(self, info):
        if info["Button"] == "BUTTON2" and info["State"] == "DOWN":
            if self.selectingFeature:
                self.endSelectionMode()

    # 3D view keyboard handler
    def KeyboardEvent(self, info):
        if info["State"] == "UP" and info["Key"] == "ESCAPE":
            if self.currentStep is None:
                self.reject()
            else:
                if self.selectingFeature:
                    self.endSelectionMode()
                else:
                    self.dismissCurrentStep()

    # selectionObserver stuff
    def addSelection(self, doc_name, obj_name, sub_name, mousePos):
        pass

    def removeSelection(self, doc_name, obj_name, sub_name, mousePos=None):
        pass

    def clearSelection(self, doc_name):
        pass
    
    def updateTaskboxFromSimulation(self):
        self.form.TimeStartSpinBox.setValue(self.simFeaturePy.aTimeStart)
        self.form.TimeEndSpinBox.setValue(self.simFeaturePy.bTimeEnd)
        self.form.TimeStepOutputSpinBox.setValue(self.simFeaturePy.cTimeStepOutput)
        self.form.TimeStepMinimumSpinBox.setValue(self.simFeaturePy.dTimeStepMinimum)
        self.form.TimeStepMaximumSpinBox.setValue(self.simFeaturePy.eTimeStepMaximum)
        self.form.GlobalErrorToleranceSpinBox.setValue(self.simFeaturePy.fGlobalErrorTolerance)
        self.form.CurrentFrameSpinBox.setValue(self.simFeaturePy.gCurrentFrame)
        self.form.StartFrameSpinBox.setValue(self.simFeaturePy.hStartFrame)
        self.form.EndFrameSpinBox.setValue(self.simFeaturePy.iEndFrame)
        self.form.FramesPerSecondSpinBox.setValue(self.simFeaturePy.jFramesPerSecond)

    def on_radio_button_toggled(self):
        assemblyDoc = UtilsAssembly.activeAssembly()
        if not assemblyDoc:
            return
        if self.form.InputStateRadioButton.isChecked():
            App.setActiveTransaction("Starting from input state")
            # assemblyDoc.updateForFrame(0)
            self.form.CurrentFrameSpinBox.setValue(0)
            App.closeActiveTransaction()
        elif self.form.InitialAssembledStateRadioButton.isChecked():
            App.setActiveTransaction("Starting from initial assembled state")
            # assemblyDoc.updateForFrame(1)
            self.form.CurrentFrameSpinBox.setValue(1)
            App.closeActiveTransaction()
        elif self.form.CurrentStateRadioButton.isChecked():
            App.setActiveTransaction("Starting from current state")
            # Do nothing
            App.closeActiveTransaction()

    def runKinematics(self):
        assemblyDoc = UtilsAssembly.activeAssembly()
        if not assemblyDoc:
            return
        # App.setActiveTransaction("Simulating from current state")
        assemblyDoc.solve()
        # App.closeActiveTransaction()
        nFrms = assemblyDoc.numberOfFrames()
        self.form.CurrentFrameSpinBox.setValue(nFrms - 1)
        self.form.StartFrameSpinBox.setValue(1)
        self.form.EndFrameSpinBox.setValue(nFrms - 1)

    def onCurrentFrameChanged(self):
        self.simFeaturePy.gCurrentFrame = self.form.CurrentFrameSpinBox.value()
        assemblyDoc = UtilsAssembly.activeAssembly()
        if not assemblyDoc:
            return
        App.setActiveTransaction("Updating to current frame number")
        assemblyDoc.updateForFrame(self.simFeaturePy.gCurrentFrame)
        App.closeActiveTransaction()

    def onStartFrameChanged(self):
        self.simFeaturePy.hStartFrame = self.form.StartFrameSpinBox.value()

    def onEndFrameChanged(self):
        self.simFeaturePy.iEndFrame = self.form.EndFrameSpinBox.value()

    def onFramesPerSecondChanged(self):
        self.simFeaturePy.jFramesPerSecond = self.form.FramesPerSecondSpinBox.value()

    def playBackward(self):
        pass
    
    def animationTimerStartForward(self):
        self.direction = 1
        self.animationTimerStart()
    
    def animationTimerStartBackward(self):
        self.direction = -1
        self.animationTimerStart()
    
    def animationTimerStart(self):
        self.animationTimer.stop();
        self.currentFrm = self.simFeaturePy.gCurrentFrame
        self.startFrm = self.simFeaturePy.hStartFrame
        self.endFrm = self.simFeaturePy.iEndFrame
        assert self.startFrm <= self.endFrm , "Animation frame error"
        self.fps = self.simFeaturePy.jFramesPerSecond
        self.deltaTime = 1.0 / self.fps
        self.startTime = time.time()
        self.index = self.currentFrm
        self.animationTimer.setInterval(self.deltaTime * 1000) # ms
        print("dt = ", self.deltaTime * 1000)
        self.animationTimer.start();
    
    def playAnimation(self):
        range = self.endFrm - self.startFrm
        offset = self.currentFrm - self.startFrm
        count = int((time.time() - self.startTime) / self.deltaTime)
        self.index = ((self.direction*count + offset) % range) + self.startFrm
        # print(self.index, time.time())
        self.form.CurrentFrameSpinBox.setValue(self.index)

    def displayLastFrame(self):
        assemblyDoc = UtilsAssembly.activeAssembly()
        nFrms = assemblyDoc.numberOfFrames()
        self.form.CurrentFrameSpinBox.setValue(nFrms - 1)

    def stepBackward(self):
        self.animationTimer.stop()
        nextFrm = self.form.CurrentFrameSpinBox.value() - 1
        if nextFrm < self.form.StartFrameSpinBox.value():
            nextFrm = self.form.EndFrameSpinBox.value() #wraparound
        if nextFrm > self.form.EndFrameSpinBox.value():
            nextFrm = self.form.EndFrameSpinBox.value()
        self.form.CurrentFrameSpinBox.setValue(nextFrm)

    def stepForward(self):
        self.animationTimer.stop()
        nextFrm = self.form.CurrentFrameSpinBox.value() + 1
        if nextFrm < self.form.StartFrameSpinBox.value():
            nextFrm = self.form.StartFrameSpinBox.value()
        if nextFrm > self.form.EndFrameSpinBox.value():
            nextFrm = self.form.StartFrameSpinBox.value() #wraparound
        self.form.CurrentFrameSpinBox.setValue(nextFrm)


if App.GuiUp:
    Gui.addCommand("Assembly_CreateSimulation", CommandCreateSimulation())
