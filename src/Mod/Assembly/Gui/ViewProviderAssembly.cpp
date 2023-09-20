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
#include <vector>
#include <sstream>
#include <iostream>
#endif

#include <App/Link.h>
#include <App/Document.h>
#include <App/DocumentObject.h>
#include <App/Part.h>
#include <Gui/Application.h>
#include <Gui/BitmapFactory.h>
#include <Gui/Command.h>
#include <Gui/MDIView.h>
#include <Gui/View3DInventor.h>
#include <Gui/View3DInventorViewer.h>
#include <Mod/Assembly/App/AssemblyObject.h>
#include <Mod/PartDesign/App/Body.h>

#include "ViewProviderAssembly.h"


using namespace Assembly;
using namespace AssemblyGui;

PROPERTY_SOURCE(AssemblyGui::ViewProviderAssembly, Gui::ViewProviderPart)

ViewProviderAssembly::ViewProviderAssembly()
    : canStartDragging(false)
    , partMoving(false)
    , numberOfSel(0)
    , prevMousePosition(Base::Vector3d(0., 0., 0.))
    , docsToMove({})
{}

ViewProviderAssembly::~ViewProviderAssembly() = default;

QIcon ViewProviderAssembly::getIcon() const
{
    return Gui::BitmapFactory().pixmap("Geoassembly.svg");
}

bool ViewProviderAssembly::doubleClicked()
{
    if (isInEditMode()) {
        // Part is already 'Active' so we exit edit mode.
        Gui::Command::doCommand(Gui::Command::Gui, "Gui.activeDocument().resetEdit()");
    }
    else {
        // Part is not 'Active' so we enter edit mode to make it so.
        Gui::Application::Instance->activeDocument()->setEdit(this);
    }

    return true;
}


bool ViewProviderAssembly::setEdit(int ModNum)
{
    // Set the part as 'Activated' ie bold in the tree.
    Gui::Command::doCommand(Gui::Command::Gui,
                            "Gui.ActiveDocument.ActiveView.setActiveObject('%s', "
                            "App.getDocument('%s').getObject('%s'))",
                            PARTKEY,
                            this->getObject()->getDocument()->getName(),
                            this->getObject()->getNameInDocument());

    return true;
}

void ViewProviderAssembly::unsetEdit(int ModNum)
{
    Q_UNUSED(ModNum);

    canStartDragging = false;
    partMoving = false;
    docsToMove = {};

    // Set the part as not 'Activated' ie not bold in the tree.
    Gui::Command::doCommand(Gui::Command::Gui,
                            "Gui.ActiveDocument.ActiveView.setActiveObject('%s', None)",
                            PARTKEY);
}

bool ViewProviderAssembly::isInEditMode()
{
    App::DocumentObject* activePart = getActivePart();
    if (!activePart) {
        return false;
    }

    return activePart == this->getObject();
}

App::DocumentObject* ViewProviderAssembly::getActivePart()
{
    App::DocumentObject* activePart = nullptr;
    auto activeDoc = Gui::Application::Instance->activeDocument();
    if (!activeDoc) {
        activeDoc = getDocument();
    }
    auto activeView = activeDoc->setActiveView(this);
    if (!activeView) {
        return nullptr;
    }

    activePart = activeView->getActiveObject<App::DocumentObject*>(PARTKEY);
    return activePart;
}

bool ViewProviderAssembly::mouseMove(const SbVec2s& cursorPos, Gui::View3DInventorViewer* viewer)
{
    // Base::Console().Warning("Mouse move\n");

    // Initialize or end the dragging of parts
    if (canStartDragging) {
        canStartDragging = false;

        if (numberOfSel != Gui::Selection().getSelectionEx().size()) {
            // This means the user released the click but the event was missed
            // because of selection.
            return false;
        }

        if (getSelectedObjectsWithinAssembly()) {
            SbVec3f vec = viewer->getPointOnFocalPlane(cursorPos);
            prevMousePosition = Base::Vector3d(vec[0], vec[1], vec[2]);

            initMove();
        }
    }

    // Do the dragging of parts
    if (partMoving) {
        SbVec3f vec = viewer->getPointOnFocalPlane(cursorPos);
        Base::Vector3d mousePosition = Base::Vector3d(vec[0], vec[1], vec[2]);
        Base::Vector3d translation = mousePosition - prevMousePosition;
        for (auto obj : docsToMove) {
            auto* propPlacement =
                dynamic_cast<App::PropertyPlacement*>(obj->getPropertyByName("Placement"));
            if (propPlacement) {
                Base::Placement plc = propPlacement->getValue();
                Base::Vector3d pos = plc.getPosition();
                pos += translation;
                Base::Placement newPlacement = Base::Placement(pos, plc.getRotation());
                propPlacement->setValue(newPlacement);
            }
        }
        prevMousePosition = mousePosition;

        AssemblyObject* assemblyPart = static_cast<AssemblyObject*>(getObject());
        assemblyPart->solve();
    }
    return false;
}

bool ViewProviderAssembly::mouseButtonPressed(int Button,
                                              bool pressed,
                                              const SbVec2s& cursorPos,
                                              const Gui::View3DInventorViewer* viewer)
{
    // Left Mouse button ****************************************************
    if (Button == 1) {
        if (pressed) {
            canStartDragging = true;

            // release event is not received when user click on a part for selection.
            // So we use this work around to know if something got selected.
            numberOfSel = Gui::Selection().getSelectionEx().size();
        }
        else {  // Button 1 released
            canStartDragging = false;
            if (partMoving) {
                endMove();
                return true;
            }
        }
    }

    return false;
}

bool ViewProviderAssembly::getSelectedObjectsWithinAssembly()
{
    // check the current selection, and check if any of the selected objects are within this
    // App::Part
    //  If any, put them into the vector docsToMove and return true.
    //  Get the document
    Gui::Document* doc = Gui::Application::Instance->activeDocument();

    if (!doc) {
        return false;
    }

    // Get the assembly object for this ViewProvider
    AssemblyObject* assemblyPart = static_cast<AssemblyObject*>(getObject());

    if (!assemblyPart) {
        return false;
    }

    for (auto& selObj : Gui::Selection().getSelectionEx("",
                                                        App::DocumentObject::getClassTypeId(),
                                                        Gui::ResolveMode::NoResolve)) {
        std::vector<std::string> subNames = selObj.getSubNames();

        App::DocumentObject* obj = getObjectFromSubNames(subNames);
        if (!obj) {
            continue;
        }

        // Check if the selected object is a child of the assembly
        if (assemblyPart->hasObject(obj, true)) {
            docsToMove.push_back(obj);
        }
    }

    // This function is called before the selection is updated. So if a user click and drag a part
    // it is not selected at that point. So we need to get the preselection too.
    if (Gui::Selection().hasPreselection()) {

        Base::Console().Warning("Gui::Selection().getPreselection().pSubName %s\n",
                                Gui::Selection().getPreselection().pSubName);
        std::vector<std::string> subNames;
        std::string subName;
        std::istringstream subNameStream(Gui::Selection().getPreselection().pSubName);
        while (std::getline(subNameStream, subName, '.')) {
            subNames.push_back(subName);
        }

        App::DocumentObject* preselectedObj = getObjectFromSubNames(subNames);
        if (preselectedObj) {
            if (assemblyPart->hasObject(preselectedObj, true)) {
                bool alreadyIn = false;
                for (const auto& obj : docsToMove) {
                    if (obj == preselectedObj) {
                        alreadyIn = true;
                        break;
                    }
                }

                if (!alreadyIn) {
                    docsToMove.push_back(preselectedObj);
                }
            }
        }
    }

    return !docsToMove.empty();
}

App::DocumentObject* ViewProviderAssembly::getObjectFromSubNames(std::vector<std::string>& subNames)
{
    App::Document* appDoc = App::GetApplication().getActiveDocument();

    std::string objName;
    if (subNames.size() < 2) {
        return nullptr;
    }
    else if (subNames.size() == 2) {
        // If two subnames then it can't be a body and the object we want is the first one
        // For example we want box in "box.face1"
        return appDoc->getObject(subNames[0].c_str());
    }
    else {
        objName = subNames[subNames.size() - 3];

        App::DocumentObject* obj = appDoc->getObject(objName.c_str());
        if (!obj) {
            return nullptr;
        }
        if (obj->getTypeId().isDerivedFrom(PartDesign::Body::getClassTypeId())) {
            return obj;
        }
        else if (obj->getTypeId().isDerivedFrom(App::Link::getClassTypeId())) {

            App::Link* link = dynamic_cast<App::Link*>(obj);

            App::DocumentObject* linkedObj = link->getLinkedObject(true);

            if (linkedObj->getTypeId().isDerivedFrom(PartDesign::Body::getClassTypeId())) {
                return obj;
            }
        }

        // then its neither a body or a link to a body.
        objName = subNames[subNames.size() - 2];
        return appDoc->getObject(objName.c_str());
    }
}

void ViewProviderAssembly::initMove()
{
    partMoving = true;

    // prevent selection while moving
    auto* view = dynamic_cast<Gui::View3DInventor*>(
        Gui::Application::Instance->editDocument()->getActiveView());
    if (view) {
        Gui::View3DInventorViewer* viewerNotConst;
        viewerNotConst = static_cast<Gui::View3DInventor*>(view)->getViewer();
        viewerNotConst->setSelectionEnabled(false);
    }
}

void ViewProviderAssembly::endMove()
{
    docsToMove = {};
    partMoving = false;
    canStartDragging = false;

    // enable selection after the move
    auto* view = dynamic_cast<Gui::View3DInventor*>(
        Gui::Application::Instance->editDocument()->getActiveView());
    if (view) {
        Gui::View3DInventorViewer* viewerNotConst;
        viewerNotConst = static_cast<Gui::View3DInventor*>(view)->getViewer();
        viewerNotConst->setSelectionEnabled(true);
    }
}
