// SPDX-License-Identifier: LGPL-2.1-or-later
/****************************************************************************
 *                                                                          *
 *   Copyright (c) 2023 Ondsel <development@ondsel.com>                     *
 *                                                                          *
 *   This file is part of FreeCAD.                                          *
 *                                                                          *
 *   FreeCAD is free software: you can redistribute it and/or modify it     *
 *   under the terms of the GNU Lesser General Public License as            *
 *   published by the Free Software Foundation, either version 2.1 of the   *
 *   License, or (at your option) any later version.                        *
 *                                                                          *
 *   FreeCAD is distributed in the hope that it will be useful, but         *
 *   WITHOUT ANY WARRANTY; without even the implied warranty of             *
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU       *
 *   Lesser General Public License for more details.                        *
 *                                                                          *
 *   You should have received a copy of the GNU Lesser General Public       *
 *   License along with FreeCAD. If not, see                                *
 *   <https://www.gnu.org/licenses/>.                                       *
 *                                                                          *
 ***************************************************************************/

#include "PreCompiled.h"
#ifndef _PreComp_
#include <BRepAdaptor_Curve.hxx>
#include <BRepAdaptor_Surface.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Face.hxx>
#include <cmath>
#include <vector>
#include <unordered_map>
#endif

#include <App/Application.h>
#include <App/Document.h>
#include <App/DocumentObjectGroup.h>
#include <App/FeaturePythonPyImp.h>
#include <App/PropertyPythonObject.h>
#include <Base/Console.h>
#include <Base/Placement.h>
#include <Base/Rotation.h>
#include <Base/Tools.h>
#include <Base/Interpreter.h>

#include <Mod/Part/App/PartFeature.h>
#include <Mod/Part/App/TopoShape.h>

#include <OndselSolver/CREATE.h>
#include <OndselSolver/ASMTSimulationParameters.h>
#include <OndselSolver/ASMTAssembly.h>
#include <OndselSolver/ASMTMarker.h>
#include <OndselSolver/ASMTPart.h>
#include <OndselSolver/ASMTJoint.h>
#include <OndselSolver/ASMTFixedJoint.h>
#include <OndselSolver/ASMTRevoluteJoint.h>
#include <OndselSolver/ASMTCylindricalJoint.h>
#include <OndselSolver/ASMTTranslationalJoint.h>
#include <OndselSolver/ASMTSphericalJoint.h>
#include <OndselSolver/ASMTPointInPlaneJoint.h>
#include <OndselSolver/ASMTTime.h>
#include <OndselSolver/ASMTConstantGravity.h>

#include "AssemblyObject.h"
#include "AssemblyObjectPy.h"
#include "JointGroup.h"

namespace PartApp = Part;

using namespace Assembly;
using namespace MbD;

PROPERTY_SOURCE(Assembly::AssemblyObject, App::Part)

AssemblyObject::AssemblyObject()
    : mbdAssembly(std::make_shared<ASMTAssembly>())
{}

AssemblyObject::~AssemblyObject() = default;

PyObject* AssemblyObject::getPyObject()
{
    if (PythonObject.is(Py::_None())) {
        // ref counter is set to 1
        PythonObject = Py::Object(new AssemblyObjectPy(this), true);
    }
    return Py::new_reference_to(PythonObject);
}

std::vector<App::DocumentObject*> AssemblyObject::getJoints()
{
    std::vector<App::DocumentObject*> joints = {};

    JointGroup* jointGroup = getJointGroup();
    if (!jointGroup) {
        return {};
    }

    Base::PyGILStateLocker lock;
    for (auto obj : jointGroup->getObjects()) {
        if (!obj) {
            continue;
        }

        auto proxy = dynamic_cast<App::PropertyPythonObject*>(obj->getPropertyByName("Proxy"));
        if (proxy) {
            Py::Object joint = proxy->getValue();
            if (joint.hasAttr("setJointConnectors")) {
                joints.push_back(obj);
            }
        }
    }

    // Make sure the joints are up to date.
    recomputeJointPlacements(joints);

    return joints;
}

void AssemblyObject::removeUnconnectedJoints(std::vector<App::DocumentObject*>& joints,
                                             std::vector<App::DocumentObject*> groundedObjs)
{
    std::set<App::DocumentObject*> connectedParts;

    // Initialize connectedParts with groundedObjs
    for (auto* groundedObj : groundedObjs) {
        connectedParts.insert(groundedObj);
    }

    // Perform a traversal from each grounded object
    for (auto* groundedObj : groundedObjs) {
        traverseAndMarkConnectedParts(groundedObj, connectedParts, joints);
    }

    // Filter out unconnected joints
    joints.erase(
        std::remove_if(
            joints.begin(),
            joints.end(),
            [&connectedParts, this](App::DocumentObject* joint) {
                App::DocumentObject* obj1 = getLinkObjFromProp(joint, "Object1");
                App::DocumentObject* obj2 = getLinkObjFromProp(joint, "Object2");
                if ((connectedParts.find(obj1) == connectedParts.end())
                    || (connectedParts.find(obj2) == connectedParts.end())) {
                    Base::Console().Warning(
                        "%s is unconnected to a grounded part so it is ignored.\n",
                        joint->getFullName());
                    return true;  // Remove joint if any connected object is not in connectedParts
                }
                return false;
            }),
        joints.end());
}

void AssemblyObject::traverseAndMarkConnectedParts(App::DocumentObject* currentObj,
                                                   std::set<App::DocumentObject*>& connectedParts,
                                                   const std::vector<App::DocumentObject*>& joints)
{
    // getConnectedParts returns the objs connected to the currentObj by any joint
    auto connectedObjs = getConnectedParts(currentObj, joints);
    for (auto* nextObj : connectedObjs) {
        if (connectedParts.find(nextObj) == connectedParts.end()) {
            connectedParts.insert(nextObj);
            traverseAndMarkConnectedParts(nextObj, connectedParts, joints);
        }
    }
}

std::vector<App::DocumentObject*>
AssemblyObject::getConnectedParts(App::DocumentObject* part,
                                  const std::vector<App::DocumentObject*>& joints)
{
    std::vector<App::DocumentObject*> connectedParts;
    for (auto joint : joints) {
        App::DocumentObject* obj1 = getLinkObjFromProp(joint, "Object1");
        App::DocumentObject* obj2 = getLinkObjFromProp(joint, "Object2");
        if (obj1 == part) {
            connectedParts.push_back(obj2);
        }
        else if (obj2 == part) {
            connectedParts.push_back(obj1);
        }
    }
    return connectedParts;
}

JointGroup* AssemblyObject::getJointGroup()
{
    App::Document* doc = getDocument();

    std::vector<DocumentObject*> jointGroups =
        doc->getObjectsOfType(Assembly::JointGroup::getClassTypeId());
    if (jointGroups.empty()) {
        return nullptr;
    }
    for (auto jointGroup : jointGroups) {
        if (hasObject(jointGroup)) {
            return dynamic_cast<JointGroup*>(jointGroup);
        }
    }
    return nullptr;
}

std::vector<App::DocumentObject*> AssemblyObject::fixGroundedParts()
{
    JointGroup* jointGroup = getJointGroup();
    if (!jointGroup) {
        return {};
    }

    std::vector<App::DocumentObject*> groundedObjs;

    Base::PyGILStateLocker lock;
    for (auto obj : jointGroup->getObjects()) {
        if (!obj) {
            continue;
        }

        auto* propObj = dynamic_cast<App::PropertyLink*>(obj->getPropertyByName("ObjectToGround"));

        if (propObj) {
            App::DocumentObject* objToGround = propObj->getValue();

            Base::Placement plc = getPlacementFromProp(obj, "Placement");
            std::string str = obj->getFullName();
            fixGroundedPart(objToGround, plc, str);
            groundedObjs.push_back(objToGround);
        }
    }
    return groundedObjs;
}

void AssemblyObject::fixGroundedPart(App::DocumentObject* obj,
                                     Base::Placement& plc,
                                     std::string& name)
{
    std::string markerName1 = "marker-" + obj->getFullName();
    auto mbdMarker1 = makeMbdMarker(markerName1, plc);
    mbdAssembly->addMarker(mbdMarker1);

    std::shared_ptr<ASMTPart> mbdPart = getMbDPart(obj);

    std::string markerName2 = "FixingMarker";
    Base::Placement basePlc = Base::Placement();
    auto mbdMarker2 = makeMbdMarker(markerName2, basePlc);
    mbdPart->addMarker(mbdMarker2);

    markerName1 = "/OndselAssembly/" + mbdMarker1->name;
    markerName2 = "/OndselAssembly/" + mbdPart->name + "/" + mbdMarker2->name;

    auto mbdJoint = CREATE<ASMTFixedJoint>::With();
    mbdJoint->setName(name);
    mbdJoint->setMarkerI(markerName1);
    mbdJoint->setMarkerJ(markerName2);

    mbdAssembly->addJoint(mbdJoint);
}

void AssemblyObject::jointParts(std::vector<App::DocumentObject*> joints)
{
    for (auto* joint : joints) {
        if (!joint) {
            continue;
        }

        std::vector<std::shared_ptr<MbD::ASMTJoint>> mbdJoints = makeMbdJoint(joint);
        for (auto& mbdJoint : mbdJoints) {
            mbdAssembly->addJoint(mbdJoint);
        }
    }
}

int AssemblyObject::solve()
{
    mbdAssembly = makeMbdAssembly();
    objectPartMap.clear();

    std::vector<App::DocumentObject*> groundedObjs = fixGroundedParts();
    if (groundedObjs.empty()) {
        // If no part fixed we can't solve.
        return -6;
    }

    std::vector<App::DocumentObject*> joints = getJoints();

    removeUnconnectedJoints(joints, groundedObjs);

    jointParts(joints);

    try {
        mbdAssembly->solve();
    }
    catch (...) {
        Base::Console().Error("Solve failed\n");
        return -1;
    }

    setNewPlacements();

    // The Placement1 and Placement2 of each joint needs to be updated as the parts moved.
    // Note calling only recomputeJointPlacements makes a weird illegal storage access
    // When solving while moving part. Happens in Py::Callable(attr).apply();
    // it apparently can't access the JointObject 'updateJCSPlacements' function.
    getJoints();

    return 0;
}

void AssemblyObject::exportAsASMT(std::string fileName)
{
    mbdAssembly = makeMbdAssembly();
    objectPartMap.clear();
    fixGroundedParts();

    std::vector<App::DocumentObject*> joints = getJoints();

    jointParts(joints);

    mbdAssembly->outputFile(fileName);
}

std::shared_ptr<ASMTJoint> AssemblyObject::makeMbdJointOfType(App::DocumentObject* joint,
                                                              JointType jointType)
{
    std::shared_ptr<ASMTJoint> mbdJoint;

    if (jointType == JointType::Fixed) {
        mbdJoint = CREATE<ASMTFixedJoint>::With();
    }
    else if (jointType == JointType::Revolute) {
        mbdJoint = CREATE<ASMTRevoluteJoint>::With();
    }
    else if (jointType == JointType::Cylindrical) {
        mbdJoint = CREATE<ASMTCylindricalJoint>::With();
    }
    else if (jointType == JointType::Slider) {
        mbdJoint = CREATE<ASMTTranslationalJoint>::With();
    }
    else if (jointType == JointType::Ball) {
        mbdJoint = CREATE<ASMTSphericalJoint>::With();
    }
    else if (jointType == JointType::Distance) {
        // Depending on the type of element of the JCS, we apply the correct set of constraints.
        std::string type1 = getElementTypeFromProp(joint, "Element1");
        std::string type2 = getElementTypeFromProp(joint, "Element2");
        const char* elName1 = getElementFromProp(joint, "Element1");
        const char* elName2 = getElementFromProp(joint, "Element2");
        auto* obj1 = getLinkedObjFromProp(joint, "Object1");
        auto* obj2 = getLinkedObjFromProp(joint, "Object2");

        if (type1 == "Vertex" && type2 == "Vertex") {
            // Point to point distance, or ball joint if offset=0.
        }
        else if (type1 == "Edge" && type2 == "Edge") {
            // Line to line distance, or cylindricalJoint if offset=0. For arcs/others ?
            if (isEdgeType(obj1, elName1, GeomAbs_Line)
                && isEdgeType(obj2, elName2, GeomAbs_Line)) {
                // TODO
            }
            else if ((isEdgeType(obj1, elName1, GeomAbs_Line)
                      && isEdgeType(obj2, elName2, GeomAbs_Circle))
                     || (isEdgeType(obj1, elName1, GeomAbs_Circle)
                         && isEdgeType(obj2, elName2, GeomAbs_Line))) {

                if (isEdgeType(obj1, elName1, GeomAbs_Circle)
                    && isEdgeType(obj2, elName2, GeomAbs_Line)) {
                    swapJCS(joint);
                    std::swap(elName1, elName2);
                    std::swap(obj1, obj2);
                }
                // TODO
            }
            else if (isEdgeType(obj1, elName1, GeomAbs_Circle)
                     && isEdgeType(obj2, elName2, GeomAbs_Circle)) {
                // TODO
            }
            else if (isEdgeType(obj1, elName1, GeomAbs_Ellipse)) {
                // TODO
            }
        }
        else if (type1 == "Face" && type2 == "Face") {
            // Co-planar (with offset if necessary) for planes. Tangent constraint for cylinder?
            if (isFaceType(obj1, elName1, GeomAbs_Plane)
                && isFaceType(obj2, elName2, GeomAbs_Plane)) {
                // TODO
            }
            else if ((isFaceType(obj1, elName1, GeomAbs_Plane)
                      && isFaceType(obj2, elName2, GeomAbs_Cylinder))
                     || (isFaceType(obj1, elName1, GeomAbs_Cylinder)
                         && isFaceType(obj2, elName2, GeomAbs_Plane))) {

                if (isFaceType(obj1, elName1, GeomAbs_Cylinder)
                    && isFaceType(obj2, elName2, GeomAbs_Plane)) {
                    swapJCS(joint);
                    std::swap(elName1, elName2);
                    std::swap(obj1, obj2);
                }
                // TODO
            }
            else if (isFaceType(obj1, elName1, GeomAbs_Cylinder)
                     && isFaceType(obj2, elName2, GeomAbs_Cylinder)) {
                // TODO
            }
            else if (isFaceType(obj1, elName1, GeomAbs_Cone)) {
                // TODO Cone, Sphere, Thorus ...
            }
        }
        else if ((type1 == "Vertex" && type2 == "Face") || (type1 == "Face" && type2 == "Vertex")) {
            if (type1 == "Vertex") {
                swapJCS(joint);
                std::swap(elName1, elName2);
                std::swap(obj1, obj2);
            }
            if (isFaceType(obj1, elName1, GeomAbs_Plane)) {
                std::shared_ptr<ASMTPointInPlaneJoint> mbdPipJoint =
                    CREATE<ASMTPointInPlaneJoint>::With();
                mbdPipJoint->offset = getJointOffset(joint);
                return mbdPipJoint;
            }
            else if (isFaceType(obj1, elName1, GeomAbs_Cylinder)) {
                // TODO
            }
            else if (isFaceType(obj1, elName1, GeomAbs_Cone)) {
                // TODO
            }
        }
        else if ((type1 == "Edge" && type2 == "Face") || (type1 == "Face" && type2 == "Edge")) {
            if (type1 == "Edge") {
                swapJCS(joint);
                std::swap(elName1, elName2);
                std::swap(obj1, obj2);
            }
            // Line in plane joint.
        }
        else if ((type1 == "Vertex" && type2 == "Edge") || (type1 == "Edge" && type2 == "Vertex")) {
            if (type1 == "Vertex") {
                swapJCS(joint);
                std::swap(elName1, elName2);
                std::swap(obj1, obj2);
            }
            if (isEdgeType(obj1, elName1, GeomAbs_Line)) {
                // Make point on line joint.
                // std::shared_ptr<ASMTPointInLineJoint> mbdPilJoint =
                // CREATE<ASMTPointInLineJoint>::With(); mbdPilJoint->offset =
                // getJointOffset(joint); return mbdPilJoint;
            }
            else if (isEdgeType(obj1, elName1, GeomAbs_Circle)) {
                // TODO
            }
            else if (isEdgeType(obj1, elName1, GeomAbs_Ellipse)) {
                // TODO
            }
            else if (isEdgeType(obj1, elName1, GeomAbs_Parabola)) {
                // TODO
            }
        }
    }

    return mbdJoint;
}

std::vector<std::shared_ptr<MbD::ASMTJoint>>
AssemblyObject::makeMbdJoint(App::DocumentObject* joint)
{
    JointType jointType = getJointType(joint);

    std::shared_ptr<ASMTJoint> mbdJoint = makeMbdJointOfType(joint, jointType);
    if (!mbdJoint) {
        return {};
    }

    std::string fullMarkerName1 = handleOneSideOfJoint(joint, jointType, "Object1", "Placement1");
    std::string fullMarkerName2 = handleOneSideOfJoint(joint, jointType, "Object2", "Placement2");

    mbdJoint->setMarkerI(fullMarkerName1);
    mbdJoint->setMarkerJ(fullMarkerName2);

    return {mbdJoint};
}
std::string AssemblyObject::handleOneSideOfJoint(App::DocumentObject* joint,
                                                 JointType jointType,
                                                 const char* propLinkName,
                                                 const char* propPlcName)
{
    App::DocumentObject* obj = getLinkObjFromProp(joint, propLinkName);

    std::shared_ptr<ASMTPart> mbdPart = getMbDPart(obj);
    Base::Placement objPlc = getPlacementFromProp(obj, "Placement");
    Base::Placement plc = getPlacementFromProp(joint, propPlcName);
    // Now we have plc which is the JCS placement, but its relative to the doc origin, not to the
    // obj.

    plc = objPlc.inverse() * plc;

    // Now we apply the offset if required.
    if (propLinkName == "Object2" && jointUseOffset(jointType)) {
        applyOffsetToPlacement(plc, joint);
    }

    std::string markerName = joint->getFullName();
    auto mbdMarker = makeMbdMarker(markerName, plc);
    mbdPart->addMarker(mbdMarker);

    return "/OndselAssembly/" + mbdPart->name + "/" + markerName;
}

std::shared_ptr<ASMTPart> AssemblyObject::getMbDPart(App::DocumentObject* obj)
{
    std::shared_ptr<ASMTPart> mbdPart;

    Base::Placement plc = getPlacementFromProp(obj, "Placement");

    auto it = objectPartMap.find(obj);
    if (it != objectPartMap.end()) {
        // obj has been associated with an ASMTPart before
        mbdPart = it->second;
    }
    else {
        // obj has not been associated with an ASMTPart before
        std::string str = obj->getFullName();
        mbdPart = makeMbdPart(str, plc);
        mbdAssembly->addPart(mbdPart);
        objectPartMap[obj] = mbdPart;  // Store the association
    }

    return mbdPart;
}

std::shared_ptr<ASMTPart>
AssemblyObject::makeMbdPart(std::string& name, Base::Placement plc, double mass)
{
    auto mdbPart = CREATE<ASMTPart>::With();
    mdbPart->setName(name);

    auto massMarker = CREATE<ASMTPrincipalMassMarker>::With();
    massMarker->setMass(mass);
    massMarker->setDensity(1.0);
    massMarker->setMomentOfInertias(1.0, 1.0, 1.0);
    mdbPart->setPrincipalMassMarker(massMarker);

    Base::Vector3d pos = plc.getPosition();
    mdbPart->setPosition3D(pos.x, pos.y, pos.z);
    // Base::Console().Warning("MbD Part placement : (%f, %f, %f)\n", pos.x, pos.y, pos.z);

    // TODO : replace with quaternion to simplify
    Base::Rotation rot = plc.getRotation();
    Base::Matrix4D mat;
    rot.getValue(mat);
    Base::Vector3d r0 = mat.getRow(0);
    Base::Vector3d r1 = mat.getRow(1);
    Base::Vector3d r2 = mat.getRow(2);
    mdbPart->setRotationMatrix(r0.x, r0.y, r0.z, r1.x, r1.y, r1.z, r2.x, r2.y, r2.z);
    /*double q0, q1, q2, q3;
    rot.getValue(q0, q1, q2, q3);
    mdbPart->setQuarternions(q0, q1, q2, q3);*/

    return mdbPart;
}

std::shared_ptr<ASMTAssembly> AssemblyObject::makeMbdAssembly()
{
    auto assembly = CREATE<ASMTAssembly>::With();
    assembly->setName("OndselAssembly");

    return assembly;
}

std::shared_ptr<ASMTMarker> AssemblyObject::makeMbdMarker(std::string& name, Base::Placement& plc)
{
    auto mbdMarker = CREATE<ASMTMarker>::With();
    mbdMarker->setName(name);

    Base::Vector3d pos = plc.getPosition();
    mbdMarker->setPosition3D(pos.x, pos.y, pos.z);

    // TODO : replace with quaternion to simplify
    Base::Rotation rot = plc.getRotation();
    Base::Matrix4D mat;
    rot.getValue(mat);
    Base::Vector3d r0 = mat.getRow(0);
    Base::Vector3d r1 = mat.getRow(1);
    Base::Vector3d r2 = mat.getRow(2);
    mbdMarker->setRotationMatrix(r0.x, r0.y, r0.z, r1.x, r1.y, r1.z, r2.x, r2.y, r2.z);
    /*double q0, q1, q2, q3;
    rot.getValue(q0, q1, q2, q3);
    mbdMarker->setQuarternions(q0, q1, q2, q3);*/
    return mbdMarker;
}

void AssemblyObject::swapJCS(App::DocumentObject* joint)
{
    auto propElement1 = dynamic_cast<App::PropertyString*>(joint->getPropertyByName("Element1"));
    auto propElement2 = dynamic_cast<App::PropertyString*>(joint->getPropertyByName("Element2"));
    if (propElement1 && propElement2) {
        auto temp = std::string(propElement1->getValue());
        propElement1->setValue(propElement2->getValue());
        propElement2->setValue(temp);
    }
    auto propVertex1 = dynamic_cast<App::PropertyString*>(joint->getPropertyByName("Vertex1"));
    auto propVertex2 = dynamic_cast<App::PropertyString*>(joint->getPropertyByName("Vertex2"));
    if (propVertex1 && propVertex2) {
        auto temp = std::string(propVertex1->getValue());
        propVertex1->setValue(propVertex2->getValue());
        propVertex2->setValue(temp);
    }
    auto propPlacement1 =
        dynamic_cast<App::PropertyPlacement*>(joint->getPropertyByName("Placement1"));
    auto propPlacement2 =
        dynamic_cast<App::PropertyPlacement*>(joint->getPropertyByName("Placement2"));
    if (propPlacement1 && propPlacement2) {
        auto temp = propPlacement1->getValue();
        propPlacement1->setValue(propPlacement2->getValue());
        propPlacement2->setValue(temp);
    }
    auto propObject1 = dynamic_cast<App::PropertyLink*>(joint->getPropertyByName("Object1"));
    auto propObject2 = dynamic_cast<App::PropertyLink*>(joint->getPropertyByName("Object2"));
    if (propObject1 && propObject2) {
        auto temp = propObject1->getValue();
        propObject1->setValue(propObject2->getValue());
        propObject2->setValue(temp);
    }
}

void AssemblyObject::applyOffsetToPlacement(Base::Placement& plc, App::DocumentObject* joint)
{
    double offset = getJointOffset(joint);

    Base::Vector3d pos = plc.getPosition();
    Base::Rotation rot = plc.getRotation();

    // OffsetVec needs to be relative to plc.
    Base::Vector3d offsetVec = Base::Vector3d(0., 0., offset);
    offsetVec = rot.multVec(offsetVec);

    pos += offsetVec;
    plc.setPosition(pos);
}

bool AssemblyObject::jointUseOffset(JointType jointType)
{
    // These are the joints needing the offset to be applied on freecad side.
    return (jointType == JointType::Fixed || jointType == JointType::Revolute);
}

void AssemblyObject::setNewPlacements()
{
    for (auto& pair : objectPartMap) {
        App::DocumentObject* obj = pair.first;
        std::shared_ptr<ASMTPart> mbdPart = pair.second;

        if (!obj || !mbdPart) {
            continue;
        }

        // Check if the object has a "Placement" property
        auto* propPlacement =
            dynamic_cast<App::PropertyPlacement*>(obj->getPropertyByName("Placement"));
        if (propPlacement) {

            double x, y, z;
            mbdPart->getPosition3D(x, y, z);
            // Base::Console().Warning("in set placement : (%f, %f, %f)\n", x, y, z);
            Base::Vector3d pos = Base::Vector3d(x, y, z);

            // TODO : replace with quaternion to simplify
            auto& r0 = mbdPart->rotationMatrix->at(0);
            auto& r1 = mbdPart->rotationMatrix->at(1);
            auto& r2 = mbdPart->rotationMatrix->at(2);
            Base::Vector3d row0 = Base::Vector3d(r0->at(0), r0->at(1), r0->at(2));
            Base::Vector3d row1 = Base::Vector3d(r1->at(0), r1->at(1), r1->at(2));
            Base::Vector3d row2 = Base::Vector3d(r2->at(0), r2->at(1), r2->at(2));
            Base::Matrix4D mat;
            mat.setRow(0, row0);
            mat.setRow(1, row1);
            mat.setRow(2, row2);
            Base::Rotation rot = Base::Rotation(mat);

            /*double q0, q1, q2, q3;
            mbdPart->getQuarternions(q0, q1, q2, q3);
            Base::Rotation rot = Base::Rotation(q0, q1, q2, q3);*/

            Base::Placement newPlacement = Base::Placement(pos, rot);

            propPlacement->setValue(newPlacement);
        }
    }
}

void AssemblyObject::recomputeJointPlacements(std::vector<App::DocumentObject*> joints)
{
    // The Placement1 and Placement2 of each joint needs to be updated as the parts moved.
    for (auto* joint : joints) {

        App::PropertyPythonObject* proxy = joint
            ? dynamic_cast<App::PropertyPythonObject*>(joint->getPropertyByName("Proxy"))
            : nullptr;

        if (!proxy) {
            continue;
        }

        Py::Object jointPy = proxy->getValue();

        if (!jointPy.hasAttr("updateJCSPlacements")) {
            continue;
        }

        Py::Object attr = jointPy.getAttr("updateJCSPlacements");
        if (attr.ptr() && attr.isCallable()) {
            Py::Tuple args(1);
            args.setItem(0, Py::asObject(joint->getPyObject()));
            Py::Callable(attr).apply(args);
        }
    }
}

double AssemblyObject::getObjMass(App::DocumentObject* obj)
{
    for (auto& pair : objMasses) {
        if (pair.first == obj) {
            return pair.second;
        }
    }
    return 1.0;
}

void AssemblyObject::setObjMasses(std::vector<std::pair<App::DocumentObject*, double>> objectMasses)
{
    objMasses = objectMasses;
}

bool AssemblyObject::isFaceType(App::DocumentObject* obj,
                                const char* elName,
                                GeomAbs_SurfaceType type)
{
    PartApp::Feature* base = static_cast<PartApp::Feature*>(obj);
    const PartApp::TopoShape& TopShape = base->Shape.getShape();

    // Check for valid face types
    TopoDS_Face face = TopoDS::Face(TopShape.getSubShape(elName));
    BRepAdaptor_Surface sf(face);
    // GeomAbs_Plane GeomAbs_Cylinder GeomAbs_Cone
    if (sf.GetType() == type) {
        return true;
    }

    return false;
}

bool AssemblyObject::isEdgeType(App::DocumentObject* obj,
                                const char* elName,
                                GeomAbs_CurveType type)
{
    PartApp::Feature* base = static_cast<PartApp::Feature*>(obj);
    const PartApp::TopoShape& TopShape = base->Shape.getShape();

    // Check for valid face types
    TopoDS_Edge edge = TopoDS::Edge(TopShape.getSubShape(elName));
    BRepAdaptor_Curve sf(edge);

    if (sf.GetType() == type) {
        return true;
    }

    return false;
}

// getters to get from properties
double AssemblyObject::getJointOffset(App::DocumentObject* joint)
{
    double offset = 0.0;

    auto* prop = dynamic_cast<App::PropertyFloat*>(joint->getPropertyByName("Offset"));
    if (prop) {
        offset = prop->getValue();
    }

    return offset;
}

JointType AssemblyObject::getJointType(App::DocumentObject* joint)
{
    JointType jointType = JointType::Fixed;

    auto* prop = dynamic_cast<App::PropertyEnumeration*>(joint->getPropertyByName("JointType"));
    if (prop) {
        jointType = static_cast<JointType>(prop->getValue());
    }

    return jointType;
}

const char* AssemblyObject::getElementFromProp(App::DocumentObject* obj, const char* propName)
{
    auto* prop = dynamic_cast<App::PropertyString*>(obj->getPropertyByName(propName));
    if (!prop) {
        return "";
    }

    return prop->getValue();
}

std::string AssemblyObject::getElementTypeFromProp(App::DocumentObject* obj, const char* propName)
{
    // The prop is going to be something like 'Edge14' or 'Face7'. We need 'Edge' or 'Face'
    std::string elementType;
    for (char ch : std::string(getElementFromProp(obj, propName))) {
        if (std::isalpha(ch)) {
            elementType += ch;
        }
    }
    return elementType;
}

App::DocumentObject* AssemblyObject::getLinkObjFromProp(App::DocumentObject* joint,
                                                        const char* propLinkName)
{
    auto* propObj = dynamic_cast<App::PropertyLink*>(joint->getPropertyByName(propLinkName));
    if (!propObj) {
        return nullptr;
    }
    return propObj->getValue();
}

App::DocumentObject* AssemblyObject::getLinkedObjFromProp(App::DocumentObject* joint,
                                                          const char* propLinkName)
{
    return getLinkObjFromProp(joint, propLinkName)->getLinkedObject(true);
}

Base::Placement AssemblyObject::getPlacementFromProp(App::DocumentObject* obj, const char* propName)
{
    Base::Placement plc = Base::Placement();
    auto* propPlacement = dynamic_cast<App::PropertyPlacement*>(obj->getPropertyByName(propName));
    if (propPlacement) {
        plc = propPlacement->getValue();
    }
    return plc;
}

/*void Part::handleChangedPropertyType(Base::XMLReader& reader, const char* TypeName, App::Property*
prop)
{
    App::Part::handleChangedPropertyType(reader, TypeName, prop);
}*/

/* Apparently not necessary as App::Part doesn't have this.
// Python Assembly feature ---------------------------------------------------------

namespace App
{
    /// @cond DOXERR
    PROPERTY_SOURCE_TEMPLATE(Assembly::AssemblyObjectPython, Assembly::AssemblyObject)
        template<>
    const char* Assembly::AssemblyObjectPython::getViewProviderName() const
    {
        return "AssemblyGui::ViewProviderAssembly";
    }
    template<>
    PyObject* Assembly::AssemblyObjectPython::getPyObject()
    {
        if (PythonObject.is(Py::_None())) {
            // ref counter is set to 1
            PythonObject = Py::Object(new FeaturePythonPyT<AssemblyObjectPy>(this), true);
        }
        return Py::new_reference_to(PythonObject);
    }
    /// @endcond

    // explicit template instantiation
    template class AssemblyExport FeaturePythonT<Assembly::AssemblyObject>;
}// namespace App*/
