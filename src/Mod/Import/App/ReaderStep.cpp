// SPDX-License-Identifier: LGPL-2.1-or-later

/***************************************************************************
 *   Copyright (c) 2023 Werner Mayer <wmayer[at]users.sourceforge.net>     *
 *                                                                         *
 *   This file is part of FreeCAD.                                         *
 *                                                                         *
 *   FreeCAD is free software: you can redistribute it and/or modify it    *
 *   under the terms of the GNU Lesser General Public License as           *
 *   published by the Free Software Foundation, either version 2.1 of the  *
 *   License, or (at your option) any later version.                       *
 *                                                                         *
 *   FreeCAD is distributed in the hope that it will be useful, but        *
 *   WITHOUT ANY WARRANTY; without even the implied warranty of            *
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU      *
 *   Lesser General Public License for more details.                       *
 *                                                                         *
 *   You should have received a copy of the GNU Lesser General Public      *
 *   License along with FreeCAD. If not, see                               *
 *   <https://www.gnu.org/licenses/>.                                      *
 *                                                                         *
 **************************************************************************/


#include "PreCompiled.h"
#ifndef _PreComp_
#include <Standard_Version.hxx>
#include <STEPCAFControl_Reader.hxx>
#include <Transfer_TransientProcess.hxx>
#include <XSControl_TransferReader.hxx>
#include <XSControl_WorkSession.hxx>
#endif

#include "ReaderStep.h"
#include <Base/Exception.h>
#include <Mod/Part/App/encodeFilename.h>
#include <Mod/Part/App/ProgressIndicator.h>
#include <Interface_Static.hxx>

using namespace Import;

ReaderStep::ReaderStep(const Base::FileInfo& file)  // NOLINT
    : file {file}
{
#if OCC_VERSION_HEX >= 0x070800
    codePage = Resource_FormatType_UTF8;
#endif
}

void ReaderStep::read(Handle(TDocStd_Document) hDoc)  // NOLINT
{
    std::string utf8Name = file.filePath();
    std::string name8bit = Part::encodeFilename(utf8Name);
    STEPCAFControl_Reader aReader;
    aReader.SetColorMode(true);
    aReader.SetNameMode(true);
    aReader.SetLayerMode(true);
    aReader.SetSHUOMode(true);
#if OCC_VERSION_HEX < 0x070800
    if (aReader.ReadFile(name8bit.c_str()) != IFSelect_RetDone) {
#else
    Handle(StepData_StepModel) aStepModel = new StepData_StepModel;
    aStepModel->InternalParameters.InitFromStatic();
    aStepModel->SetSourceCodePage(codePage);
    // These come from static init read of StepData_ConfParameters however
    // https://dev.opencascade.org/content/stepcontrolreader-readprecisionvalue says it won't really
    // affect shape healing performance - a 7.9+ version of OpenCascade might.
    // aStepModel->InternalParameters.ReadMaxPrecisionMode =
    // StepData_ConfParameters::ReadMode_MaxPrecision_Preferred ; //  _Forced or _Preferred
    // aStepModel->InternalParameters.ReadMaxPrecisionVal = Precision::Confusion();
    if (aReader.ReadFile(name8bit.c_str(), aStepModel->InternalParameters) != IFSelect_RetDone) {
#endif
        throw Base::FileException("Cannot read STEP file", file);
    }

#if OCC_VERSION_HEX < 0x070500
    Handle(Message_ProgressIndicator) pi = new Part::ProgressIndicator(100);
    aReader.Reader().WS()->MapReader()->SetProgress(pi);
    pi->NewScope(100, "Reading STEP file...");
    pi->Show();
#endif
    // Documentation is at
    // https://dev.opencascade.org/doc/overview/html/occt_user_guides__step.html#occt_step_2_3_3
    // in the section read.step.resource.name and read.step.sequence  There is a hidden config file
    // that controls how step processing is done, and can disable things like Shape Fixes -
    // ShapeFix_Shape consumes about 25% of the transfer processing time.  This code replaces that
    // special file.  Note that there are dozens of STEP loader control options in that file; see
    // src/XSTEPResource/STEP in the OpenCascade source for an example.
    if (!Interface_Static::SetCVal("read.step.sequence", "")) {
        // We failed to override the step sequence, but there isn't really an advantage in throwing
        // an exception or even issuing a warning message - just proceed with the default step read
        // sequence which will be slower.
    }

    aReader.Transfer(hDoc);
#if OCC_VERSION_HEX < 0x070500
    pi->EndScope();
#endif
}
