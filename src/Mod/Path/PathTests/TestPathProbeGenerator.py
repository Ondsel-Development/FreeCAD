# -*- coding: utf-8 -*-
# ***************************************************************************
# *   Copyright (c) 2021 sliptonic <shopinthewoods@gmail.com>               *
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
import Part
import Path
import Path.Base.Generator.probe as generator
import PathTests.PathTestUtils as PathTestUtils

Path.Log.setLevel(Path.Log.Level.INFO, Path.Log.thisModule())
Path.Log.trackModule(Path.Log.thisModule())


class TestPathProbeGenerator(PathTestUtils.PathTestBase):
    def test00(self):
        """Test Basic Probe Generator Return"""
        v1 = FreeCAD.Vector(5, 10, 10)

        result = generator.generate(v1)

        self.assertTrue(type(result) is list)
        self.assertTrue(type(result[0]) is Path.Command)

        command = result[0]

        self.assertTrue(command.Name == "G38.3")
        self.assertTrue(command.Parameters["X"] == 5)
        self.assertTrue(command.Parameters["Y"] == 10)
        self.assertTrue(command.Parameters["Z"] == 10)

    def test10(self):
        """Test signal Probe Generator Return"""
        v1 = FreeCAD.Vector(5, 10, 10)

        result = generator.generate(v1, signal=True)

        self.assertTrue(type(result) is list)
        self.assertTrue(type(result[0]) is Path.Command)

        command = result[0]

        self.assertTrue(command.Name == "G38.2")
        self.assertTrue(command.Parameters["X"] == 5)
        self.assertTrue(command.Parameters["Y"] == 10)
        self.assertTrue(command.Parameters["Z"] == 10)

