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

import FreeCAD as App

if App.GuiUp:
    import FreeCADGui as Gui

# translate = App.Qt.translate

__title__ = "Assembly utilitary functions"
__author__ = "Ondsel"
__url__ = "https://www.freecad.org"


def activeAssembly():
    doc = Gui.ActiveDocument

    if doc is None or doc.ActiveView is None:
        return None

    active_part = doc.ActiveView.getActiveObject("part")

    if active_part is not None and active_part.Type == "Assembly":
        return active_part

    return None


def isDocTemporary(doc):
    # Guard against older versions of FreeCad which don't have the Temporary attribute
    try:
        temp = doc.Temporary
    except AttributeError:
        temp = False
    return temp


def getObject(full_name):
    # full_name is "Assembly.Assembly1.LinkOrPart1.Box.Edge16"
    # or           "Assembly.Assembly1.LinkOrPart1.Body.pad.Edge16"
    # We want either Body or Box.
    parts = full_name.split(".")
    doc = App.ActiveDocument
    if len(parts) < 3:
        App.Console.PrintError(
            "getObject() in UtilsAssembly.py the object name is too short, at minimum it should be something like 'Assembly.Box.edge16'. It shouldn't be shorter"
        )
        return None

    obj = doc.getObject(parts[-3])  # So either 'Body', or 'Assembly'

    if not obj:
        return None

    if obj.TypeId == "PartDesign::Body":
        return obj
    elif obj.TypeId == "App::Link":
        linked_obj = obj.getLinkedObject()
        if linked_obj.TypeId == "PartDesign::Body":
            return obj

    # primitive, fastener, gear ... or link to primitive, fastener, gear...
    return doc.getObject(parts[-2])


def getContainingPart(full_name, selected_object):
    # full_name is "Assembly.Assembly1.LinkOrPart1.Box.Edge16"
    # or           "Assembly.Assembly1.LinkOrPart1.Body.pad.Edge16"
    # We want either Body or Box.
    parts = full_name.split(".")
    doc = App.ActiveDocument
    if len(parts) < 3:
        App.Console.PrintError(
            "getContainingPart() in UtilsAssembly.py the object name is too short, at minimum it should be something like 'Assembly.Box.edge16'. It shouldn't be shorter"
        )
        return None

    for objName in parts:
        obj = doc.getObject(objName)

        if not obj:
            continue

        # Note here we may want to specify a specific behavior for Assembly::AssemblyObject.
        if obj.TypeId == "App::Part":
            if obj.hasObject(selected_object, True):
                return obj

        elif obj.TypeId == "App::Link":
            linked_obj = obj.getLinkedObject()
            if linked_obj.TypeId == "App::Part":
                if linked_obj.hasObject(selected_object, True):
                    return obj

    # no container found so we return the object itself.
    return selected_object


# The container is used to support cases where the same object appears at several places
# which happens when you have a link to a part.
def getGlobalPlacement(targetObj, container=None):
    for part in App.activeDocument().RootObjects:
        inContainerBranch = (part == container) or (container == None)
        foundPlacement = getTargetPlacementRelativeTo(targetObj, part, container, inContainerBranch)
        if foundPlacement is not None:
            foundPlacement = part.Placement * foundPlacement
            return foundPlacement

    return App.Placement()


def getTargetPlacementRelativeTo(targetObj, part, container, inContainerBranch):
    if targetObj == part and inContainerBranch:
        return targetObj.Placement

    if part.TypeId == "App::Part" or part.TypeId == "Assembly::AssemblyObject":
        for obj in part.OutList:
            inContainerBranch = inContainerBranch or (obj == container)
            foundPlacement = getTargetPlacementRelativeTo(
                targetObj, obj, container, inContainerBranch
            )
            if foundPlacement is None:
                continue

            foundPlacement = part.Placement * foundPlacement
            return foundPlacement

    if part.TypeId == "App::Link":
        linked_obj = part.getLinkedObject()
        if linked_obj.TypeId == "App::Part" or linked_obj.TypeId == "Assembly::AssemblyObject":
            for obj in linked_obj.OutList:
                inContainerBranch = inContainerBranch or (obj == container)
                foundPlacement = getTargetPlacementRelativeTo(
                    targetObj, obj, container, inContainerBranch
                )
                if foundPlacement is None:
                    continue

                foundPlacement = part.Placement * foundPlacement
                return foundPlacement

    return None


def getElementName(full_name):
    # full_name is "Assembly.Assembly1.Assembly2.Assembly3.Box.Edge16"
    # We want either Edge16.
    parts = full_name.split(".")

    if len(parts) < 3:
        # At minimum "Assembly.Box.edge16". It shouldn't be shorter
        return ""

    return parts[-1]


def getObjsNamesAndElement(obj_name, sub_name):
    # if obj_name = "Assembly" and sub_name = "Assembly1.Assembly2.Assembly3.Box.Edge16"
    # this will return ["Assembly","Assembly1","Assembly2","Assembly3","Box"] and "Edge16"

    parts = sub_name.split(".")

    # The last part is always the element name even if empty
    element_name = parts[-1]

    # The remaining parts are object names
    obj_names = parts[:-1]
    obj_names.insert(0, obj_name)

    return obj_names, element_name


def getFullObjName(obj_name, sub_name):
    # if obj_name = "Assembly" and sub_name = "Assembly1.Assembly2.Assembly3.Box.Edge16"
    # this will return "Assembly.Assembly1.Assembly2.Assembly3.Box"
    objs_names, element_name = getObjsNamesAndElement(obj_name, sub_name)
    return ".".join(objs_names)


def getFullElementName(obj_name, sub_name):
    # if obj_name = "Assembly" and sub_name = "Assembly1.Assembly2.Assembly3.Box.Edge16"
    # this will return "Assembly.Assembly1.Assembly2.Assembly3.Box.Edge16"
    return obj_name + "." + sub_name


def extract_type_and_number(element_name):
    element_type = ""
    element_number = ""

    for char in element_name:
        if char.isalpha():
            # If the character is a letter, it's part of the type
            element_type += char
        elif char.isdigit():
            # If the character is a digit, it's part of the number
            element_number += char
        else:
            break

    if element_type and element_number:
        element_number = int(element_number)
        return element_type, element_number
    else:
        return None, None


def findElementClosestVertex(selection_dict):
    elt_type, elt_index = extract_type_and_number(selection_dict["element_name"])

    if elt_type == "Vertex":
        return selection_dict["element_name"]

    elif elt_type == "Edge":
        edge = selection_dict["object"].Shape.Edges[elt_index - 1]

        curve = edge.Curve
        if curve.TypeId == "Part::GeomCircle":
            # For centers, as they are not shape vertexes, we return the element name.
            # For now we only allow selecting the center of arcs / circles.
            return selection_dict["element_name"]

        edge_points = getPointsFromVertexes(edge.Vertexes)
        closest_vertex_index, _ = findClosestPointToMousePos(
            edge_points, selection_dict["mouse_pos"]
        )
        vertex_name = findVertexNameInObject(
            edge.Vertexes[closest_vertex_index], selection_dict["object"]
        )

        return vertex_name

    elif elt_type == "Face":
        face = selection_dict["object"].Shape.Faces[elt_index - 1]

        # Handle the circle/arc edges for their centers
        center_points = []
        center_points_edge_indexes = []
        edges = face.Edges

        for i, edge in enumerate(edges):
            curve = edge.Curve
            if curve.TypeId == "Part::GeomCircle":
                center_points.append(curve.Location)
                center_points_edge_indexes.append(i)

        if len(center_points) > 0:
            closest_center_index, closest_center_distance = findClosestPointToMousePos(
                center_points, selection_dict["mouse_pos"]
            )

        # Hendle the face vertexes
        face_points = getPointsFromVertexes(face.Vertexes)
        closest_vertex_index, closest_vertex_distance = findClosestPointToMousePos(
            face_points, selection_dict["mouse_pos"]
        )

        if len(center_points) > 0:
            if closest_center_distance < closest_vertex_distance:
                # Note the index here is the index within the face! Not the object.
                index = center_points_edge_indexes[closest_center_index] + 1
                return "Edge" + str(index)

        vertex_name = findVertexNameInObject(
            face.Vertexes[closest_vertex_index], selection_dict["object"]
        )

        return vertex_name

    return ""


def getPointsFromVertexes(vertexes):
    points = []
    for vtx in vertexes:
        points.append(vtx.Point)
    return points


def findClosestPointToMousePos(candidates_points, mousePos):
    closest_point_index = None
    point_min_length = None

    for i, point in enumerate(candidates_points):
        length = (mousePos - point).Length
        if closest_point_index is None or length < point_min_length:
            closest_point_index = i
            point_min_length = length

    return closest_point_index, point_min_length


def findVertexNameInObject(vertex, obj):
    for i, vtx in enumerate(obj.Shape.Vertexes):
        if vtx.Point == vertex.Point:
            return "Vertex" + str(i + 1)
    return ""


def color_from_unsigned(c):
    return [
        float(int((c >> 24) & 0xFF) / 255),
        float(int((c >> 16) & 0xFF) / 255),
        float(int((c >> 8) & 0xFF) / 255),
    ]


def getJointGroup(assembly):
    joint_group = assembly.getObject("Joints")

    if not joint_group:
        joint_group = assembly.newObject("Assembly::JointGroup", "Joints")
    return joint_group


def isAssemblyGrounded():
    assembly = activeAssembly()
    if not assembly:
        return False

    jointGroup = getJointGroup(assembly)

    for joint in jointGroup.Group:
        if hasattr(joint, "ObjectToGround"):
            return True

    return False
