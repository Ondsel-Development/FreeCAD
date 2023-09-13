# -*- coding: utf-8 -*-
# ***************************************************************************
# *   Copyright (c) 2023 sliptonic <shopinthewoods@gmail.com>               *
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


import Path
import FreeCAD


__title__ = "Probing Path Generator"
__author__ = "sliptonic (Brad Collette)"
__url__ = "https://www.freecad.org"
__doc__ = "Generates the drilling toolpath for a single spotshape"


if False:
    Path.Log.setLevel(Path.Log.Level.DEBUG, Path.Log.thisModule())
    Path.Log.trackModule(Path.Log.thisModule())
else:
    Path.Log.setLevel(Path.Log.Level.INFO, Path.Log.thisModule())


def generate(probevector, signal=False):
    """
    Generates Gcode for probing a single point.

    Takes as input a vector for the location to be probed.

    Assuming basic functionality present in linuxcnc probing operations
    https://linuxcnc.org/docs/2.6/html/gcode/gcode.html#sec:G38-probe

    if signal is True, generate a G38.2 command which will signal an error if the probe fails.
    otherwise generate a G38.3 command which will not signal an error if the probe fails.

    G38.4 - probe away from workpiece, stop on loss of contact, signal error if failure - Not supported
    G38.5 - probe away from workpiece, stop on loss of contact - Not supported

    TODO:  The probe generator can be expanded to handle probing in different contexts.  For example,
    On Machine Inspection (OMI) would need to output significantly more complex gcode to handle probing
    a location and then comparing the probe results to the expected value and either notifying the operator
    or writing the results to an inspection file.

    """

    Path.Log.debug(probevector)
    if not type(probevector) == FreeCAD.Vector:
        raise ValueError("probeVector must be a vector")

    cmd = "G38.2" if signal else "G38.3"

    cmdParams = {}
    cmdParams["X"] = probevector.x
    cmdParams["Y"] = probevector.y
    cmdParams["Z"] = probevector.z

    return [Path.Command(cmd, cmdParams)]
