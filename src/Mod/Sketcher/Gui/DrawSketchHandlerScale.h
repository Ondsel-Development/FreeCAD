/***************************************************************************
 *   Copyright (c) 2022 Boyer Pierre-Louis <pierrelouis.boyer@gmail.com>   *
 *                                                                         *
 *   This file is part of the FreeCAD CAx development system.              *
 *                                                                         *
 *   This library is free software; you can redistribute it and/or         *
 *   modify it under the terms of the GNU Library General Public           *
 *   License as published by the Free Software Foundation; either          *
 *   version 2 of the License, or (at your option) any later version.      *
 *                                                                         *
 *   This library  is distributed in the hope that it will be useful,      *
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
 *   GNU Library General Public License for more details.                  *
 *                                                                         *
 *   You should have received a copy of the GNU Library General Public     *
 *   License along with this library; see the file COPYING.LIB. If not,    *
 *   write to the Free Software Foundation, Inc., 59 Temple Place,         *
 *   Suite 330, Boston, MA  02111-1307, USA                                *
 *                                                                         *
 ***************************************************************************/


#ifndef SKETCHERGUI_DrawSketchHandlerScale_H
#define SKETCHERGUI_DrawSketchHandlerScale_H

#include "DrawSketchDefaultWidgetController.h"
#include "DrawSketchControllableHandler.h"

#include "GeometryCreationMode.h"
#include "Utils.h"

namespace SketcherGui
{

extern GeometryCreationMode geometryCreationMode;  // defined in CommandCreateGeo.cpp

class DrawSketchHandlerScale;

using DSHScaleController =
    DrawSketchDefaultWidgetController<DrawSketchHandlerScale,
                                      StateMachines::ThreeSeekEnd,
                                      /*PAutoConstraintSize =*/0,
                                      /*OnViewParametersT =*/OnViewParameters<3>,
                                      /*WidgetParametersT =*/WidgetParameters<0>,
                                      /*WidgetCheckboxesT =*/WidgetCheckboxes<1>,
                                      /*WidgetComboboxesT =*/WidgetComboboxes<0>>;

using DSHScaleControllerBase = DSHScaleController::ControllerBase;

using DrawSketchHandlerScaleBase = DrawSketchControllableHandler<DSHScaleController>;

class DrawSketchHandlerScale: public DrawSketchHandlerScaleBase
{
    friend DSHScaleController;
    friend DSHScaleControllerBase;

public:
    explicit DrawSketchHandlerScale(std::vector<int> listOfGeoIds)
        : listOfGeoIds(listOfGeoIds)
        , deleteOriginal(true)
    {}
    ~DrawSketchHandlerScale() override = default;

private:
    void updateDataAndDrawToPosition(Base::Vector2d onSketchPos) override
    {

        switch (state()) {
            case SelectMode::SeekFirst: {
                referencePoint = onSketchPos;
                referencePoint = onSketchPos;
            } break;
            case SelectMode::SeekSecond: {
                refLength = (onSketchPos - referencePoint).Length();

                startPoint = onSketchPos;

                if (refLength > Precision::Confusion()) {
                    std::vector<Part::Geometry*> geometriesToAdd;
                    auto* line = new Part::GeomLineSegment();
                    line->setPoints(toVector3d(referencePoint), toVector3d(startPoint));
                    geometriesToAdd.push_back(line);
                    drawEdit(geometriesToAdd);
                }
            } break;
            case SelectMode::SeekThird: {
                length = (onSketchPos - referencePoint).Length();
                endPoint = onSketchPos;
                scaleFactor = length / refLength;

                CreateAndDrawShapeGeometry();
            } break;
            default:
                break;
        }
    }

    void executeCommands() override
    {
        try {
            Gui::Command::openCommand(QT_TRANSLATE_NOOP("Command", "Scale geometries"));

            createShape(false);

            commandAddShapeGeometryAndConstraints();

            if (deleteOriginal) {
                deleteOriginalGeos();
            }

            Gui::Command::commitCommand();
        }
        catch (const Base::Exception& e) {
            Gui::NotifyError(sketchgui,
                             QT_TRANSLATE_NOOP("Notifications", "Error"),
                             QT_TRANSLATE_NOOP("Notifications", "Failed to scale"));

            Gui::Command::abortCommand();
            THROWM(Base::RuntimeError,
                   QT_TRANSLATE_NOOP(
                       "Notifications",
                       "Tool execution aborted") "\n")  // This prevents constraints from being
                                                        // applied on non existing geometry
        }
    }

    void createAutoConstraints() override
    {
        // none
    }

    std::string getToolName() const override
    {
        return "DSH_Scale";
    }

    QString getCrosshairCursorSVGName() const override
    {
        return QString::fromLatin1("Sketcher_Pointer_Create_Scale");
    }

    std::unique_ptr<QWidget> createWidget() const override
    {
        return std::make_unique<SketcherToolDefaultWidget>();
    }

    bool isWidgetVisible() const override
    {
        return true;
    };

    QPixmap getToolIcon() const override
    {
        return Gui::BitmapFactory().pixmap("Sketcher_Scale");
    }

    QString getToolWidgetText() const override
    {
        return QString(QObject::tr("Scale parameters"));
    }

    void activated() override
    {
        DrawSketchDefaultHandler::activated();
        continuousMode = false;
    }

private:
    std::vector<int> listOfGeoIds;
    Base::Vector2d referencePoint, startPoint, endPoint;
    bool deleteOriginal;
    double refLength, length, scaleFactor;

    void deleteOriginalGeos()
    {
        std::stringstream stream;
        for (size_t j = 0; j < listOfGeoIds.size() - 1; j++) {
            stream << listOfGeoIds[j] << ",";
        }
        stream << listOfGeoIds[listOfGeoIds.size() - 1];
        try {
            Gui::cmdAppObjectArgs(sketchgui->getObject(),
                                  "delGeometries([%s])",
                                  stream.str().c_str());
        }
        catch (const Base::Exception& e) {
            Base::Console().Error("%s\n", e.what());
        }
    }

    void createShape(bool onlyeditoutline) override
    {
        if (fabs(scaleFactor) < Precision::Confusion()) {
            return;
        }

        Sketcher::SketchObject* Obj = sketchgui->getSketchObject();

        ShapeGeometry.clear();

        for (auto& geoId : listOfGeoIds) {
            Part::Geometry* geo = Obj->getGeometry(geoId)->copy();

            bool isConstructionGeo =
                Sketcher::GeometryFacade::getConstruction(Obj->getGeometry(geoId));
            Sketcher::GeometryFacade::setConstruction(geo, isConstructionGeo);

            if (isCircle(*geo)) {
                auto* circle = static_cast<Part::GeomCircle*>(geo);
                circle->setRadius(circle->getRadius() * scaleFactor);
                circle->setCenter(getScaledPoint(circle->getCenter(), referencePoint, scaleFactor));
            }
            else if (isArcOfCircle(*geo)) {
                auto* arcOfCircle = static_cast<Part::GeomArcOfCircle*>(geo);
                arcOfCircle->setRadius(arcOfCircle->getRadius() * scaleFactor);
                arcOfCircle->setCenter(
                    getScaledPoint(arcOfCircle->getCenter(), referencePoint, scaleFactor));
            }
            else if (isLineSegment(*geo)) {
                auto* line = static_cast<Part::GeomLineSegment*>(geo);
                line->setPoints(getScaledPoint(line->getStartPoint(), referencePoint, scaleFactor),
                                getScaledPoint(line->getEndPoint(), referencePoint, scaleFactor));
            }
            else if (isEllipse(*geo)) {
                auto* ellipse = static_cast<Part::GeomEllipse*>(geo);
                ellipse->setMajorRadius(ellipse->getMajorRadius() * scaleFactor);
                ellipse->setMinorRadius(ellipse->getMinorRadius() * scaleFactor);
                ellipse->setCenter(
                    getScaledPoint(ellipse->getCenter(), referencePoint, scaleFactor));
            }
            else if (isArcOfEllipse(*geo)) {
                auto* arcOfEllipse = static_cast<Part::GeomArcOfEllipse*>(geo);
                arcOfEllipse->setMajorRadius(arcOfEllipse->getMajorRadius() * scaleFactor);
                arcOfEllipse->setMinorRadius(arcOfEllipse->getMinorRadius() * scaleFactor);
                arcOfEllipse->setCenter(
                    getScaledPoint(arcOfEllipse->getCenter(), referencePoint, scaleFactor));
            }
            else if (isArcOfHyperbola(*geo)) {
                auto* arcOfHyperbola = static_cast<Part::GeomArcOfHyperbola*>(geo);
                arcOfHyperbola->setMajorRadius(arcOfHyperbola->getMajorRadius() * scaleFactor);
                arcOfHyperbola->setMinorRadius(arcOfHyperbola->getMinorRadius() * scaleFactor);
                arcOfHyperbola->setCenter(
                    getScaledPoint(arcOfHyperbola->getCenter(), referencePoint, scaleFactor));
            }
            else if (isArcOfParabola(*geo)) {
                auto* arcOfParabola = static_cast<Part::GeomArcOfParabola*>(geo);
                // TODO: Problem with scale parabola end points.
                arcOfParabola->setFocal(arcOfParabola->getFocal() * scaleFactor);
                arcOfParabola->setCenter(
                    getScaledPoint(arcOfParabola->getCenter(), referencePoint, scaleFactor));
            }
            else if (isBSplineCurve(*geo)) {
                auto* bSpline = static_cast<Part::GeomBSplineCurve*>(geo);
                std::vector<Base::Vector3d> poles = bSpline->getPoles();
                for (size_t p = 0; p < poles.size(); p++) {
                    poles[p] = getScaledPoint(poles[p], referencePoint, scaleFactor);
                }
                bSpline->setPoles(poles);
            }
            else if (isPoint(*geo)) {
                auto* point = static_cast<Part::GeomPoint*>(geo);
                point->setPoint(getScaledPoint(point->getPoint(), referencePoint, scaleFactor));
            }

            ShapeGeometry.push_back(std::move(std::unique_ptr<Part::Geometry>(geo)));
        }

        if (onlyeditoutline) {
            // Add the lines to show lengths
            addLineToShapeGeometry(toVector3d(referencePoint), toVector3d(startPoint), true);

            addLineToShapeGeometry(toVector3d(referencePoint), toVector3d(endPoint), true);
        }
        else {
            int firstCurveCreated = getHighestCurveIndex() + 1;
            using namespace Sketcher;

            const std::vector<Constraint*>& vals = Obj->Constraints.getValues();
            std::vector<int> geoIdsWhoAlreadyHasEqual =
                {};  // avoid applying equal several times if cloning distanceX and distanceY of the
                     // same part.

            for (auto& cstr : vals) {
                int firstIndex = indexInVec(listOfGeoIds, cstr->First);
                int secondIndex = indexInVec(listOfGeoIds, cstr->Second);
                int thirdIndex = indexInVec(listOfGeoIds, cstr->Third);

                auto newConstr = std::make_unique<Constraint>();
                newConstr->Type = cstr->Type;
                newConstr->FirstPos = cstr->FirstPos;
                newConstr->SecondPos = cstr->SecondPos;
                newConstr->ThirdPos = cstr->ThirdPos;
                newConstr->First = firstCurveCreated + firstIndex;

                if ((cstr->Type == Symmetric || cstr->Type == Tangent
                     || cstr->Type == Perpendicular)
                    && firstIndex >= 0 && secondIndex >= 0 && thirdIndex >= 0) {
                    newConstr->Second = firstCurveCreated + secondIndex;
                    newConstr->Third = firstCurveCreated + thirdIndex;
                }
                else if ((cstr->Type == Coincident || cstr->Type == Tangent
                          || cstr->Type == Symmetric || cstr->Type == Perpendicular
                          || cstr->Type == Parallel || cstr->Type == Equal
                          || cstr->Type == PointOnObject)
                         && firstIndex >= 0 && secondIndex >= 0
                         && thirdIndex == GeoEnum::GeoUndef) {
                    newConstr->Second = firstCurveCreated + secondIndex;
                }
                else if ((cstr->Type == Radius || cstr->Type == Diameter || cstr->Type == Weight)
                         && firstIndex >= 0) {
                    newConstr->setValue(newConstr->getValue() * scaleFactor);
                }
                else if ((cstr->Type == Distance || cstr->Type == DistanceX
                          || cstr->Type == DistanceY)
                         && firstIndex >= 0 && secondIndex >= 0) {
                    newConstr->Second = firstCurveCreated + secondIndex;
                    newConstr->setValue(newConstr->getValue() * scaleFactor);
                }
                else if ((cstr->Type == Block) && firstIndex >= 0) {
                    newConstr->First = firstCurveCreated + firstIndex;
                }
                else {
                    continue;
                }

                ShapeConstraints.push_back(std::move(newConstr));
            }
        }
    }

    int indexInVec(std::vector<int> vec, int elem)
    {
        if (elem == Sketcher::GeoEnum::GeoUndef) {
            return Sketcher::GeoEnum::GeoUndef;
        }
        for (size_t i = 0; i < vec.size(); i++) {
            if (vec[i] == elem) {
                return i;
            }
        }
        return -1;
    }

    Base::Vector3d
    getScaledPoint(Base::Vector3d pointToScale, Base::Vector2d referencePoint, double scaleFactor)
    {
        Base::Vector2d pointToScale2D;
        pointToScale2D.x = pointToScale.x;
        pointToScale2D.y = pointToScale.y;
        pointToScale2D = (pointToScale2D - referencePoint) * scaleFactor + referencePoint;

        pointToScale.x = pointToScale2D.x;
        pointToScale.y = pointToScale2D.y;

        return pointToScale;
    }
};

template<>
auto DSHScaleControllerBase::getState(int labelindex) const
{
    switch (labelindex) {
        case OnViewParameter::First:
        case OnViewParameter::Second:
            return SelectMode::SeekFirst;
            break;
        case OnViewParameter::Third:
            return SelectMode::SeekThird;
            break;
        default:
            THROWM(Base::ValueError, "OnViewParameter index without an associated machine state")
    }
}

template<>
void DSHScaleController::configureToolWidget()
{
    if (!init) {  // Code to be executed only upon initialisation
        toolWidget->setCheckboxLabel(
            WCheckbox::FirstBox,
            QApplication::translate("TaskSketcherTool_c1_scale", "Keep original geometries (U)"));
    }

    onViewParameters[OnViewParameter::First]->setLabelType(Gui::SoDatumLabel::DISTANCEX);
    onViewParameters[OnViewParameter::Second]->setLabelType(Gui::SoDatumLabel::DISTANCEY);
}

template<>
void DSHScaleController::adaptDrawingToCheckboxChange(int checkboxindex, bool value)
{
    switch (checkboxindex) {
        case WCheckbox::FirstBox: {
            handler->deleteOriginal = !value;
        } break;
    }
}

template<>
void DSHScaleControllerBase::doEnforceControlParameters(Base::Vector2d& onSketchPos)
{

    switch (handler->state()) {
        case SelectMode::SeekFirst: {
            if (onViewParameters[OnViewParameter::First]->isSet) {
                onSketchPos.x = onViewParameters[OnViewParameter::First]->getValue();
            }

            if (onViewParameters[OnViewParameter::Second]->isSet) {
                onSketchPos.y = onViewParameters[OnViewParameter::Second]->getValue();
            }
        } break;
        case SelectMode::SeekThird: {
            if (onViewParameters[OnViewParameter::Third]->isSet) {
                double scaleFactor = onViewParameters[OnViewParameter::Third]->getValue();
                handler->startPoint = handler->referencePoint + Base::Vector2d(1.0, 0.0);
                handler->endPoint = handler->referencePoint + Base::Vector2d(scaleFactor, 0.0);

                onSketchPos = handler->endPoint;
            }
        } break;
        default:
            break;
    }
}

template<>
void DSHScaleController::adaptParameters(Base::Vector2d onSketchPos)
{
    switch (handler->state()) {
        case SelectMode::SeekFirst: {
            if (!onViewParameters[OnViewParameter::First]->isSet) {
                onViewParameters[OnViewParameter::First]->setSpinboxValue(onSketchPos.x);
            }

            if (!onViewParameters[OnViewParameter::Second]->isSet) {
                onViewParameters[OnViewParameter::Second]->setSpinboxValue(onSketchPos.y);
            }

            bool sameSign = onSketchPos.x * onSketchPos.y > 0.;
            onViewParameters[OnViewParameter::First]->setLabelAutoDistanceReverse(!sameSign);
            onViewParameters[OnViewParameter::Second]->setLabelAutoDistanceReverse(sameSign);
            onViewParameters[OnViewParameter::First]->setPoints(Base::Vector3d(),
                                                                toVector3d(onSketchPos));
            onViewParameters[OnViewParameter::Second]->setPoints(Base::Vector3d(),
                                                                 toVector3d(onSketchPos));
        } break;
        case SelectMode::SeekThird: {
            if (!onViewParameters[OnViewParameter::Third]->isSet) {
                onViewParameters[OnViewParameter::Third]->setSpinboxValue(handler->scaleFactor,
                                                                          Base::Unit());
            }

            Base::Vector3d start = toVector3d(handler->referencePoint);
            Base::Vector3d end = toVector3d(handler->endPoint);
            onViewParameters[OnViewParameter::Third]->setPoints(start, end);
        } break;
        default:
            break;
    }
}

template<>
void DSHScaleController::doChangeDrawSketchHandlerMode()
{
    switch (handler->state()) {
        case SelectMode::SeekFirst: {
            if (onViewParameters[OnViewParameter::First]->isSet
                && onViewParameters[OnViewParameter::Second]->isSet) {

                handler->setState(SelectMode::SeekSecond);
            }
        } break;
        case SelectMode::SeekThird: {
            if (onViewParameters[OnViewParameter::Third]->isSet) {

                handler->setState(SelectMode::End);
            }
        } break;
            break;
        default:
            break;
    }
}


}  // namespace SketcherGui


#endif  // SKETCHERGUI_DrawSketchHandlerScale_H
