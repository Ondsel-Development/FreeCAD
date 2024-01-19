# SPDX-License-Identifier: LGPL-2.1-or-later
# /****************************************************************************
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
# ***************************************************************************/

import math

import FreeCAD as App
import Part

from PySide import QtCore
from PySide.QtCore import QT_TRANSLATE_NOOP

if App.GuiUp:
    import FreeCADGui as Gui

# translate = App.Qt.translate

__title__ = "Assembly Joint object"
__author__ = "Ondsel"
__url__ = "https://www.freecad.org"

from pivy import coin
import UtilsAssembly

JointTypes = [
    QT_TRANSLATE_NOOP("AssemblyJoint", "Fixed"),
    QT_TRANSLATE_NOOP("AssemblyJoint", "Revolute"),
    QT_TRANSLATE_NOOP("AssemblyJoint", "Cylindrical"),
    QT_TRANSLATE_NOOP("AssemblyJoint", "Slider"),
    QT_TRANSLATE_NOOP("AssemblyJoint", "Ball"),
    QT_TRANSLATE_NOOP("AssemblyJoint", "Distance"),
]

JointUsingOffset = [
    QT_TRANSLATE_NOOP("AssemblyJoint", "Fixed"),
    QT_TRANSLATE_NOOP("AssemblyJoint", "Revolute"),
    QT_TRANSLATE_NOOP("AssemblyJoint", "Distance"),
]


class Joint:
    def __init__(self, joint, type_index):
        self.Type = "Joint"

        joint.Proxy = self

        joint.addProperty(
            "App::PropertyEnumeration",
            "JointType",
            "Joint",
            QT_TRANSLATE_NOOP("App::Property", "The type of the joint"),
        )
        joint.JointType = JointTypes  # sets the list
        joint.JointType = JointTypes[type_index]  # set the initial value

        # First Joint Connector
        joint.addProperty(
            "App::PropertyLink",
            "Object1",
            "Joint Connector 1",
            QT_TRANSLATE_NOOP("App::Property", "The first object of the joint"),
        )

        joint.addProperty(
            "App::PropertyLink",
            "Part1",
            "Joint Connector 1",
            QT_TRANSLATE_NOOP("App::Property", "The first part of the joint"),
        )

        joint.addProperty(
            "App::PropertyString",
            "Element1",
            "Joint Connector 1",
            QT_TRANSLATE_NOOP("App::Property", "The selected element of the first object"),
        )

        joint.addProperty(
            "App::PropertyString",
            "Vertex1",
            "Joint Connector 1",
            QT_TRANSLATE_NOOP("App::Property", "The selected vertex of the first object"),
        )

        joint.addProperty(
            "App::PropertyPlacement",
            "Placement1",
            "Joint Connector 1",
            QT_TRANSLATE_NOOP(
                "App::Property",
                "This is the local coordinate system within the object1 that will be used to joint.",
            ),
        )

        # Second Joint Connector
        joint.addProperty(
            "App::PropertyLink",
            "Object2",
            "Joint Connector 2",
            QT_TRANSLATE_NOOP("App::Property", "The second object of the joint"),
        )

        joint.addProperty(
            "App::PropertyLink",
            "Part2",
            "Joint Connector 2",
            QT_TRANSLATE_NOOP("App::Property", "The second part of the joint"),
        )

        joint.addProperty(
            "App::PropertyString",
            "Element2",
            "Joint Connector 2",
            QT_TRANSLATE_NOOP("App::Property", "The selected element of the second object"),
        )

        joint.addProperty(
            "App::PropertyString",
            "Vertex2",
            "Joint Connector 2",
            QT_TRANSLATE_NOOP("App::Property", "The selected vertex of the second object"),
        )

        joint.addProperty(
            "App::PropertyPlacement",
            "Placement2",
            "Joint Connector 2",
            QT_TRANSLATE_NOOP(
                "App::Property",
                "This is the local coordinate system within the object2 that will be used to joint.",
            ),
        )

        joint.addProperty(
            "App::PropertyFloat",
            "Offset",
            "Joint",
            QT_TRANSLATE_NOOP(
                "App::Property",
                "This is the offset of the joint.",
            ),
        )

        self.setJointConnectors(joint, [])

    def __getstate__(self):
        return self.Type

    def __setstate__(self, state):
        if state:
            self.Type = state

    def setJointType(self, joint, jointType):
        joint.JointType = jointType
        joint.Label = jointType.replace(" ", "")

    def onChanged(self, fp, prop):
        """Do something when a property has changed"""
        # App.Console.PrintMessage("Change property: " + str(prop) + "\n")
        pass

    def execute(self, fp):
        """Do something when doing a recomputation, this method is mandatory"""
        # App.Console.PrintMessage("Recompute Python Box feature\n")
        pass

    def setJointConnectors(self, joint, current_selection):
        # current selection is a vector of strings like "Assembly.Assembly1.Assembly2.Body.Pad.Edge16" including both what selection return as obj_name and obj_sub

        if len(current_selection) >= 1:
            joint.Object1 = current_selection[0]["object"]
            joint.Part1 = current_selection[0]["part"]
            joint.Element1 = current_selection[0]["element_name"]
            joint.Vertex1 = current_selection[0]["vertex_name"]
            joint.Placement1 = self.findPlacement(
                joint.Object1, joint.Part1, joint.Element1, joint.Vertex1
            )
        else:
            joint.Object1 = None
            joint.Element1 = ""
            joint.Vertex1 = ""
            joint.Placement1 = UtilsAssembly.activeAssembly().Placement

        if len(current_selection) >= 2:
            joint.Object2 = current_selection[1]["object"]
            joint.Part2 = current_selection[1]["part"]
            joint.Element2 = current_selection[1]["element_name"]
            joint.Vertex2 = current_selection[1]["vertex_name"]
            joint.Placement2 = self.findPlacement(
                joint.Object2, joint.Part2, joint.Element2, joint.Vertex2
            )
        else:
            joint.Object2 = None
            joint.Element2 = ""
            joint.Vertex2 = ""
            joint.Placement2 = UtilsAssembly.activeAssembly().Placement

    def setJointOffset(self, joint, offset):
        joint.Offset = offset

    def updateJCSPlacements(self, joint):
        joint.Placement1 = self.findPlacement(
            joint.Object1, joint.Part1, joint.Element1, joint.Vertex1
        )
        joint.Placement2 = self.findPlacement(
            joint.Object2, joint.Part2, joint.Element2, joint.Vertex2
        )

    """
    So here we want to find a placement that corresponds to a local coordinate system that would be placed at the selected vertex.
    - obj is usually a App::Link to a PartDesign::Body, or primitive, fasteners. But can also be directly the object.1
    - elt can be a face, an edge or a vertex.
    - If elt is a vertex, then vtx = elt And placement is vtx coordinates without rotation.
    - if elt is an edge, then vtx = edge start/end vertex depending on which is closer. If elt is an arc or circle, vtx can also be the center. The rotation is the plane normal to the line positioned at vtx. Or for arcs/circle, the plane of the arc.
    - if elt is a plane face, vtx is the face vertex (to the list of vertex we need to add arc/circle centers) the closer to the mouse. The placement is the plane rotation positioned at vtx
    - if elt is a cylindrical face, vtx can also be the center of the arcs of the cylindrical face.
    """

    def findPlacement(self, obj, part, elt, vtx):
        plc = App.Placement()

        if not obj or not elt or not vtx:
            return App.Placement()

        elt_type, elt_index = UtilsAssembly.extract_type_and_number(elt)
        vtx_type, vtx_index = UtilsAssembly.extract_type_and_number(vtx)

        if elt_type == "Vertex":
            vertex = obj.Shape.Vertexes[elt_index - 1]
            plc.Base = (vertex.X, vertex.Y, vertex.Z)
        elif elt_type == "Edge":
            edge = obj.Shape.Edges[elt_index - 1]
            curve = edge.Curve

            # First we find the translation
            if vtx_type == "Edge":
                # In this case the edge is a circle/arc and the wanted vertex is its center.
                if curve.TypeId == "Part::GeomCircle":
                    center_point = curve.Location
                    plc.Base = (center_point.x, center_point.y, center_point.z)
            else:
                vertex = obj.Shape.Vertexes[vtx_index - 1]
                plc.Base = (vertex.X, vertex.Y, vertex.Z)

            # Then we find the Rotation
            if curve.TypeId == "Part::GeomCircle":
                plc.Rotation = App.Rotation(curve.Rotation)

            if curve.TypeId == "Part::GeomLine":
                plane_normal = curve.Direction
                plane_origin = App.Vector(0, 0, 0)
                plane = Part.Plane(plane_origin, plane_normal)
                plc.Rotation = App.Rotation(plane.Rotation)

        elif elt_type == "Face":
            face = obj.Shape.Faces[elt_index - 1]

            # First we find the translation
            if vtx_type == "Edge":
                # In this case the edge is a circle/arc and the wanted vertex is its center.
                circleOrArc = face.Edges[vtx_index - 1]
                curve = circleOrArc.Curve
                if curve.TypeId == "Part::GeomCircle":
                    center_point = curve.Location
                    plc.Base = (center_point.x, center_point.y, center_point.z)

            else:
                vertex = obj.Shape.Vertexes[vtx_index - 1]
                plc.Base = (vertex.X, vertex.Y, vertex.Z)

            # Then we find the Rotation
            surface = face.Surface
            if surface.TypeId == "Part::GeomPlane":
                plc.Rotation = App.Rotation(surface.Rotation)

        # Now plc is the placement relative to the origin determined by the object placement.
        # But it does not take into account Part placements. So if the solid is in a part and
        # if the part has a placement then plc is wrong.

        obj_plc = obj.Placement
        global_plc = UtilsAssembly.getGlobalPlacement(obj, part)

        # change plc to be relative to the object placement.
        plc = obj_plc.inverse() * plc

        # change plc to be relative to the origin of the document.
        plc = global_plc * plc

        return plc


class ViewProviderJoint:
    def __init__(self, vobj):
        """Set this object to the proxy object of the actual view provider"""

        vobj.Proxy = self

    def attach(self, vobj):
        """Setup the scene sub-graph of the view provider, this method is mandatory"""
        self.axis_thickness = 3

        view_params = App.ParamGet("User parameter:BaseApp/Preferences/View")
        param_x_axis_color = view_params.GetUnsigned("AxisXColor", 0xCC333300)
        param_y_axis_color = view_params.GetUnsigned("AxisYColor", 0x33CC3300)
        param_z_axis_color = view_params.GetUnsigned("AxisZColor", 0x3333CC00)

        self.x_axis_so_color = coin.SoBaseColor()
        self.x_axis_so_color.rgb.setValue(UtilsAssembly.color_from_unsigned(param_x_axis_color))
        self.y_axis_so_color = coin.SoBaseColor()
        self.y_axis_so_color.rgb.setValue(UtilsAssembly.color_from_unsigned(param_y_axis_color))
        self.z_axis_so_color = coin.SoBaseColor()
        self.z_axis_so_color.rgb.setValue(UtilsAssembly.color_from_unsigned(param_z_axis_color))

        camera = Gui.ActiveDocument.ActiveView.getCameraNode()
        self.cameraSensor = coin.SoFieldSensor(self.camera_callback, camera)
        self.cameraSensor.attach(camera.height)

        self.app_obj = vobj.Object

        self.transform1 = coin.SoTransform()
        self.transform2 = coin.SoTransform()
        self.transform3 = coin.SoTransform()

        scaleF = self.get_JCS_size()
        self.axisScale = coin.SoScale()
        self.axisScale.scaleFactor.setValue(scaleF, scaleF, scaleF)

        self.draw_style = coin.SoDrawStyle()
        self.draw_style.style = coin.SoDrawStyle.LINES
        self.draw_style.lineWidth = self.axis_thickness

        self.switch_JCS1 = self.JCS_sep(self.transform1)
        self.switch_JCS2 = self.JCS_sep(self.transform2)
        self.switch_JCS_preview = self.JCS_sep(self.transform3)

        self.display_mode = coin.SoGroup()
        self.display_mode.addChild(self.switch_JCS1)
        self.display_mode.addChild(self.switch_JCS2)
        self.display_mode.addChild(self.switch_JCS_preview)
        vobj.addDisplayMode(self.display_mode, "Wireframe")

    def camera_callback(self, *args):
        scaleF = self.get_JCS_size()
        self.axisScale.scaleFactor.setValue(scaleF, scaleF, scaleF)

    def JCS_sep(self, soTransform):
        pick = coin.SoPickStyle()
        pick.style.setValue(coin.SoPickStyle.UNPICKABLE)

        JCS = coin.SoAnnotation()
        JCS.addChild(soTransform)
        JCS.addChild(pick)

        base_plane_sep = self.plane_sep(0.4, 15)
        X_axis_sep = self.line_sep([0.5, 0, 0], [1, 0, 0], self.x_axis_so_color)
        Y_axis_sep = self.line_sep([0, 0.5, 0], [0, 1, 0], self.y_axis_so_color)
        Z_axis_sep = self.line_sep([0, 0, 0], [0, 0, 1], self.z_axis_so_color)

        JCS.addChild(base_plane_sep)
        JCS.addChild(X_axis_sep)
        JCS.addChild(Y_axis_sep)
        JCS.addChild(Z_axis_sep)

        switch_JCS = coin.SoSwitch()
        switch_JCS.addChild(JCS)
        switch_JCS.whichChild = coin.SO_SWITCH_NONE
        return switch_JCS

    def line_sep(self, startPoint, endPoint, soColor):
        line = coin.SoLineSet()
        line.numVertices.setValue(2)
        coords = coin.SoCoordinate3()
        coords.point.setValues(0, [startPoint, endPoint])

        axis_sep = coin.SoAnnotation()
        axis_sep.addChild(self.axisScale)
        axis_sep.addChild(self.draw_style)
        axis_sep.addChild(soColor)
        axis_sep.addChild(coords)
        axis_sep.addChild(line)
        return axis_sep

    def plane_sep(self, size, num_vertices):
        coords = coin.SoCoordinate3()

        for i in range(num_vertices):
            angle = float(i) / num_vertices * 2.0 * math.pi
            x = math.cos(angle) * size
            y = math.sin(angle) * size
            coords.point.set1Value(i, x, y, 0)

        face = coin.SoFaceSet()
        face.numVertices.setValue(num_vertices)

        transform = coin.SoTransform()
        transform.translation.setValue(0, 0, 0)

        draw_style = coin.SoDrawStyle()
        draw_style.style = coin.SoDrawStyle.FILLED

        material = coin.SoMaterial()
        material.diffuseColor.setValue([1, 1, 1])
        material.ambientColor.setValue([1, 1, 1])
        material.specularColor.setValue([1, 1, 1])
        material.emissiveColor.setValue([1, 1, 1])
        material.transparency.setValue(0.7)

        face_sep = coin.SoAnnotation()
        face_sep.addChild(self.axisScale)
        face_sep.addChild(transform)
        face_sep.addChild(draw_style)
        face_sep.addChild(material)
        face_sep.addChild(coords)
        face_sep.addChild(face)
        return face_sep

    def get_JCS_size(self):
        camera = Gui.ActiveDocument.ActiveView.getCameraNode()
        if not camera:
            return 10

        return camera.height.getValue() / 20

    def set_JCS_placement(self, soTransform, placement):
        t = placement.Base
        soTransform.translation.setValue(t.x, t.y, t.z)

        r = placement.Rotation.Q
        soTransform.rotation.setValue(r[0], r[1], r[2], r[3])

    def updateData(self, fp, prop):
        """If a property of the handled feature has changed we have the chance to handle this here"""
        # fp is the handled feature, prop is the name of the property that has changed
        if prop == "Placement1":
            plc = fp.getPropertyByName("Placement1")
            if fp.getPropertyByName("Object1"):
                self.switch_JCS1.whichChild = coin.SO_SWITCH_ALL
                self.set_JCS_placement(self.transform1, plc)
            else:
                self.switch_JCS1.whichChild = coin.SO_SWITCH_NONE

        if prop == "Placement2":
            plc = fp.getPropertyByName("Placement2")
            if fp.getPropertyByName("Object2"):
                self.switch_JCS2.whichChild = coin.SO_SWITCH_ALL
                self.set_JCS_placement(self.transform2, plc)
            else:
                self.switch_JCS2.whichChild = coin.SO_SWITCH_NONE

    def showPreviewJCS(self, visible, placement=None):
        if visible:
            self.switch_JCS_preview.whichChild = coin.SO_SWITCH_ALL
            self.set_JCS_placement(self.transform3, placement)
        else:
            self.switch_JCS_preview.whichChild = coin.SO_SWITCH_NONE

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
        if prop == "color_X_axis":
            c = vp.getPropertyByName("color_X_axis")
            self.x_axis_so_color.rgb.setValue(c[0], c[1], c[2])
        if prop == "color_Y_axis":
            c = vp.getPropertyByName("color_Y_axis")
            self.x_axis_so_color.rgb.setValue(c[0], c[1], c[2])
        if prop == "color_Z_axis":
            c = vp.getPropertyByName("color_Z_axis")
            self.x_axis_so_color.rgb.setValue(c[0], c[1], c[2])

    def getIcon(self):
        if self.app_obj.JointType == "Fixed":
            return ":/icons/Assembly_CreateJointFixed.svg"
        elif self.app_obj.JointType == "Revolute":
            return ":/icons/Assembly_CreateJointRevolute.svg"
        elif self.app_obj.JointType == "Cylindrical":
            return ":/icons/Assembly_CreateJointCylindrical.svg"
        elif self.app_obj.JointType == "Slider":
            return ":/icons/Assembly_CreateJointSlider.svg"
        elif self.app_obj.JointType == "Ball":
            return ":/icons/Assembly_CreateJointBall.svg"
        elif self.app_obj.JointType == "Distance":
            return ":/icons/Assembly_CreateJointDistance.svg"

        return ":/icons/Assembly_CreateJoint.svg"

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
        panel = TaskAssemblyCreateJoint(0, vobj.Object)
        Gui.Control.showDialog(panel)


################ Grounded Joint object #################


class GroundedJoint:
    def __init__(self, joint, obj_to_ground):
        self.Type = "GoundedJoint"
        joint.Proxy = self
        self.joint = joint

        joint.addProperty(
            "App::PropertyLink",
            "ObjectToGround",
            "Ground",
            QT_TRANSLATE_NOOP("App::Property", "The object to ground"),
        )

        joint.ObjectToGround = obj_to_ground

        joint.addProperty(
            "App::PropertyPlacement",
            "Placement",
            "Ground",
            QT_TRANSLATE_NOOP(
                "App::Property",
                "This is where the part is grounded.",
            ),
        )

        joint.Placement = obj_to_ground.Placement

    def __getstate__(self):
        return self.Type

    def __setstate__(self, state):
        if state:
            self.Type = state

    def onChanged(self, fp, prop):
        """Do something when a property has changed"""
        # App.Console.PrintMessage("Change property: " + str(prop) + "\n")
        pass

    def execute(self, fp):
        """Do something when doing a recomputation, this method is mandatory"""
        # App.Console.PrintMessage("Recompute Python Box feature\n")
        pass


class ViewProviderGroundedJoint:
    def __init__(self, obj):
        """Set this object to the proxy object of the actual view provider"""
        obj.Proxy = self

    def attach(self, obj):
        """Setup the scene sub-graph of the view provider, this method is mandatory"""
        pass

    def updateData(self, fp, prop):
        """If a property of the handled feature has changed we have the chance to handle this here"""
        # fp is the handled feature, prop is the name of the property that has changed
        pass

    def getDisplayModes(self, obj):
        """Return a list of display modes."""
        modes = ["Wireframe"]
        return modes

    def getDefaultDisplayMode(self):
        """Return the name of the default display mode. It must be defined in getDisplayModes."""
        return "Wireframe"

    def onChanged(self, vp, prop):
        """Here we can do something when a single property got changed"""
        # App.Console.PrintMessage("Change property: " + str(prop) + "\n")
        pass

    def getIcon(self):
        return ":/icons/Assembly_ToggleGrounded.svg"


class MakeJointSelGate:
    def __init__(self, taskbox, assembly):
        self.taskbox = taskbox
        self.assembly = assembly

    def allow(self, doc, obj, sub):
        if not sub:
            return False

        objs_names, element_name = UtilsAssembly.getObjsNamesAndElement(obj.Name, sub)

        if self.assembly.Name not in objs_names or element_name == "":
            # Only objects within the assembly. And not whole objects, only elements.
            return False

        if Gui.Selection.isSelected(obj, sub, Gui.Selection.ResolveMode.NoResolve):
            # If it's to deselect then it's ok
            return True

        if len(self.taskbox.current_selection) >= 2:
            # No more than 2 elements can be selected for basic joints.
            return False

        full_obj_name = ".".join(objs_names)
        full_element_name = full_obj_name + "." + element_name
        selected_object = UtilsAssembly.getObject(full_element_name)
        part_containing_selected_object = UtilsAssembly.getContainingPart(
            full_element_name, selected_object
        )

        for selection_dict in self.taskbox.current_selection:
            if selection_dict["part"] == part_containing_selected_object:
                # Can't join a solid to itself. So the user need to select 2 different parts.
                return False

        return True


activeTask = None


class TaskAssemblyCreateJoint(QtCore.QObject):
    def __init__(self, jointTypeIndex, jointObj=None):
        super().__init__()

        global activeTask
        activeTask = self

        self.assembly = UtilsAssembly.activeAssembly()
        self.view = Gui.activeDocument().activeView()
        self.doc = App.ActiveDocument

        if not self.assembly or not self.view or not self.doc:
            return

        self.assembly.ViewObject.EnableMovement = False

        self.form = Gui.PySideUic.loadUi(":/panels/TaskAssemblyCreateJoint.ui")

        self.form.jointType.addItems(JointTypes)
        self.form.jointType.setCurrentIndex(jointTypeIndex)
        self.form.jointType.currentIndexChanged.connect(self.onJointTypeChanged)
        self.form.offsetSpinbox.valueChanged.connect(self.onOffsetChanged)

        Gui.Selection.clearSelection()

        if jointObj:
            self.joint = jointObj
            self.jointName = jointObj.Label
            App.setActiveTransaction("Edit " + self.jointName + " Joint")

            self.updateTaskboxFromJoint()

        else:
            self.jointName = self.form.jointType.currentText().replace(" ", "")
            App.setActiveTransaction("Create " + self.jointName + " Joint")

            self.current_selection = []
            self.preselection_dict = None

            self.createJointObject()

        self.toggleOffsetVisibility()

        Gui.Selection.addSelectionGate(
            MakeJointSelGate(self, self.assembly), Gui.Selection.ResolveMode.NoResolve
        )
        Gui.Selection.addObserver(self, Gui.Selection.ResolveMode.NoResolve)
        Gui.Selection.setSelectionStyle(Gui.Selection.SelectionStyle.GreedySelection)

        self.callbackMove = self.view.addEventCallback("SoLocation2Event", self.moveMouse)
        self.callbackKey = self.view.addEventCallback("SoKeyboardEvent", self.KeyboardEvent)

    def accept(self):
        if len(self.current_selection) != 2:
            App.Console.PrintWarning("You need to select 2 elements from 2 separate parts.")
            return False

        # Hide JSC's when joint is created and enable selection highlighting
        # self.joint.ViewObject.Visibility = False
        # self.joint.ViewObject.OnTopWhenSelected = "Enabled"

        self.deactivate()

        self.assembly.solve()

        App.closeActiveTransaction()
        return True

    def reject(self):
        self.deactivate()
        App.closeActiveTransaction(True)
        return True

    def deactivate(self):
        global activeTask
        activeTask = None

        self.assembly.ViewObject.EnableMovement = True
        Gui.Selection.removeSelectionGate()
        Gui.Selection.removeObserver(self)
        Gui.Selection.setSelectionStyle(Gui.Selection.SelectionStyle.NormalSelection)
        Gui.Selection.clearSelection()
        self.view.removeEventCallback("SoLocation2Event", self.callbackMove)
        self.view.removeEventCallback("SoKeyboardEvent", self.callbackKey)
        if Gui.Control.activeDialog():
            Gui.Control.closeDialog()

    def createJointObject(self):
        type_index = self.form.jointType.currentIndex()

        joint_group = UtilsAssembly.getJointGroup(self.assembly)

        self.joint = joint_group.newObject("App::FeaturePython", self.jointName)
        Joint(self.joint, type_index)
        ViewProviderJoint(self.joint.ViewObject)

    def onJointTypeChanged(self, index):
        self.joint.Proxy.setJointType(self.joint, self.form.jointType.currentText())
        self.toggleOffsetVisibility()

    def onOffsetChanged(self, quantity):
        self.joint.Proxy.setJointOffset(self.joint, self.form.offsetSpinbox.property("rawValue"))

    def toggleOffsetVisibility(self):
        if self.form.jointType.currentText() in JointUsingOffset:
            self.form.offsetLabel.show()
            self.form.offsetSpinbox.show()
        else:
            self.form.offsetLabel.hide()
            self.form.offsetSpinbox.hide()

    def updateTaskboxFromJoint(self):
        self.current_selection = []
        self.preselection_dict = None

        selection_dict1 = {
            "object": self.joint.Object1,
            "element_name": self.joint.Element1,
            "vertex_name": self.joint.Vertex1,
        }

        selection_dict2 = {
            "object": self.joint.Object2,
            "element_name": self.joint.Element2,
            "vertex_name": self.joint.Vertex2,
        }

        self.current_selection.append(selection_dict1)
        self.current_selection.append(selection_dict2)

        elName = self.getObjSubNameFromObj(self.joint.Object1, self.joint.Element1)
        """print(
            f"Gui.Selection.addSelection('{self.doc.Name}', '{self.joint.Object1.Name}', '{elName}')"
        )"""
        Gui.Selection.addSelection(self.doc.Name, self.joint.Object1.Name, elName)

        elName = self.getObjSubNameFromObj(self.joint.Object2, self.joint.Element2)
        Gui.Selection.addSelection(self.doc.Name, self.joint.Object2.Name, elName)

        self.form.offsetSpinbox.setProperty("rawValue", self.joint.Offset)
        self.updateJointList()

    def getObjSubNameFromObj(self, obj, elName):
        if obj.TypeId == "PartDesign::Body":
            return obj.Tip.Name + "." + elName
        elif obj.TypeId == "App::Link":
            linked_obj = obj.getLinkedObject()
            if linked_obj.TypeId == "PartDesign::Body":
                return linked_obj.Tip.Name + "." + elName
            else:
                return elName
        else:
            return elName

    def updateJoint(self):
        # First we build the listwidget
        self.updateJointList()

        # Then we pass the new list to the join object
        self.joint.Proxy.setJointConnectors(self.joint, self.current_selection)

    def updateJointList(self):
        self.form.featureList.clear()
        simplified_names = []
        for sel in self.current_selection:
            # TODO: ideally we probably want to hide the feature name in case of PartDesign bodies. ie body.face12 and not body.pad2.face12
            sname = sel["object"].Label + "." + sel["element_name"]
            simplified_names.append(sname)
        self.form.featureList.addItems(simplified_names)

    def moveMouse(self, info):
        if len(self.current_selection) >= 2 or (
            len(self.current_selection) == 1
            and self.current_selection[0]["part"] == self.preselection_dict["part"]
        ):
            self.joint.ViewObject.Proxy.showPreviewJCS(False)
            return

        cursor_pos = self.view.getCursorPos()
        cursor_info = self.view.getObjectInfo(cursor_pos)
        # cursor_info example  {'x': 41.515, 'y': 7.449, 'z': 16.861, 'ParentObject': <Part object>, 'SubName': 'Body002.Pad.Face5', 'Document': 'part3', 'Object': 'Pad', 'Component': 'Face5'}

        if (
            not cursor_info
            or not self.preselection_dict
            or cursor_info["SubName"] != self.preselection_dict["sub_name"]
        ):
            self.joint.ViewObject.Proxy.showPreviewJCS(False)
            return

        # newPos = self.view.getPoint(*info["Position"]) # This is not what we want, it's not pos on the object but on the focal plane

        newPos = App.Vector(cursor_info["x"], cursor_info["y"], cursor_info["z"])
        self.preselection_dict["mouse_pos"] = newPos

        self.preselection_dict["vertex_name"] = UtilsAssembly.findElementClosestVertex(
            self.preselection_dict
        )

        placement = self.joint.Proxy.findPlacement(
            self.preselection_dict["object"],
            self.preselection_dict["part"],
            self.preselection_dict["element_name"],
            self.preselection_dict["vertex_name"],
        )
        self.joint.ViewObject.Proxy.showPreviewJCS(True, placement)
        self.previewJCSVisible = True

    # 3D view keyboard handler
    def KeyboardEvent(self, info):
        if info["State"] == "UP" and info["Key"] == "ESCAPE":
            self.reject()

        if info["State"] == "UP" and info["Key"] == "RETURN":
            self.accept()

    # selectionObserver stuff
    def addSelection(self, doc_name, obj_name, sub_name, mousePos):
        full_obj_name = UtilsAssembly.getFullObjName(obj_name, sub_name)
        full_element_name = UtilsAssembly.getFullElementName(obj_name, sub_name)
        selected_object = UtilsAssembly.getObject(full_element_name)
        element_name = UtilsAssembly.getElementName(full_element_name)
        part_containing_selected_object = UtilsAssembly.getContainingPart(
            full_element_name, selected_object
        )

        selection_dict = {
            "object": selected_object,
            "part": part_containing_selected_object,
            "element_name": element_name,
            "full_element_name": full_element_name,
            "full_obj_name": full_obj_name,
            "mouse_pos": App.Vector(mousePos[0], mousePos[1], mousePos[2]),
        }
        selection_dict["vertex_name"] = UtilsAssembly.findElementClosestVertex(selection_dict)

        self.current_selection.append(selection_dict)
        self.updateJoint()

    def removeSelection(self, doc_name, obj_name, sub_name, mousePos=None):
        full_element_name = UtilsAssembly.getFullElementName(obj_name, sub_name)
        selected_object = UtilsAssembly.getObject(full_element_name)
        element_name = UtilsAssembly.getElementName(full_element_name)
        part_containing_selected_object = UtilsAssembly.getContainingPart(
            full_element_name, selected_object
        )

        # Find and remove the corresponding dictionary from the combined list
        selection_dict_to_remove = None
        for selection_dict in self.current_selection:
            if selection_dict["part"] == part_containing_selected_object:
                selection_dict_to_remove = selection_dict
                break

        if selection_dict_to_remove is not None:
            self.current_selection.remove(selection_dict_to_remove)

        self.updateJoint()

    def setPreselection(self, doc_name, obj_name, sub_name):
        if not sub_name:
            self.preselection_dict = None
            return

        full_obj_name = UtilsAssembly.getFullObjName(obj_name, sub_name)
        full_element_name = UtilsAssembly.getFullElementName(obj_name, sub_name)
        selected_object = UtilsAssembly.getObject(full_element_name)
        element_name = UtilsAssembly.getElementName(full_element_name)
        part_containing_selected_object = UtilsAssembly.getContainingPart(
            full_element_name, selected_object
        )

        self.preselection_dict = {
            "object": selected_object,
            "part": part_containing_selected_object,
            "sub_name": sub_name,
            "element_name": element_name,
            "full_element_name": full_element_name,
            "full_obj_name": full_obj_name,
        }

    def clearSelection(self, doc_name):
        self.current_selection.clear()
        self.updateJoint()
