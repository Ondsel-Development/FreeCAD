# -*- coding: utf-8 -*-
# ***************************************************************************
# *   Copyright (c) 2024 Ondsel <development@ondsel.com>                    *
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
import os
from Path.Post.Processor import PostProcessor
import Path
import FreeCAD
from FreeCAD import Vector
import math
from fpdf import FPDF

Path.Log.setLevel(Path.Log.Level.INFO, Path.Log.thisModule())

translate = FreeCAD.Qt.translate

debug = True
if debug:
    Path.Log.setLevel(Path.Log.Level.DEBUG, Path.Log.thisModule())
    Path.Log.trackModule(Path.Log.thisModule())
else:
    Path.Log.setLevel(Path.Log.Level.INFO, Path.Log.thisModule())

# Define colors for the layers
LAYER_COLORS = {
    "CUT": "#ff0000",
    "ENGRAVE": "#0000ff",
    "FILL": "#00ff00",
    "DEFAULT": "#000000",
}


class PdfPostProcessor(PostProcessor):
    def __init__(self, job):
        super().__init__(
            job,
            tooltip=translate("CAM", "PDF post processor"),
            tooltipargs=[],
            units="mm",
        )
        Path.Log.debug("PDF post processor initialized")

    def export(self):
        Path.Log.debug("Exporting the job")

        use_layers = "--layers" in self._job.PostProcessorArgs

        postables = self._buildPostList()
        Path.Log.debug(f"postables count: {len(postables)}")
        print(postables)

        return self.export_pdf(postables, use_layers)

    def export_pdf(self, postables, use_layers):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        for idx, section in enumerate(postables):
            self.create_pdf_section(pdf, section, idx, use_layers)

        output_path = os.path.join(self._job.Document.Path, "output.pdf")
        pdf.output(output_path)
        Path.Log.debug(f"PDF saved to {output_path}")
        return output_path

    def create_pdf_section(self, pdf, section, idx, use_layers):
        partname, sublist = section

        # Initialize bounding box
        xmin, ymin, xmax, ymax = self.calculate_bounding_box(sublist)

        if xmin is None or ymin is None or xmax is None or ymax is None:
            Path.Log.debug("No wires found, skipping section")
            return

        width = xmax - xmin
        height = ymax - ymin

        for obj_idx, obj in enumerate(sublist):
            strokestyle = self.get_stroke_style(obj)
            color = strokestyle["color"]
            pdf.set_draw_color(*self.hex_to_rgb(color))
            pdf.set_line_width(strokestyle["width"])

            wires = Path.Geom.wiresForPath(obj.Path)
            for wire in wires:
                self.wire_to_pdf_path(pdf, wire, width, height, xmin, ymin)

    def wire_to_pdf_path(self, pdf, wire, width, height, xmin, ymin):
        """Convert FreeCAD wire to PDF path data with y-axis inversion"""
        is_first_point = True
        start_x, start_y = None, None

        for edge in wire.Edges:
            start_point = edge.Vertexes[0].Point
            end_point = edge.Vertexes[-1].Point

            if is_first_point:
                start_x, start_y = start_point.x - xmin, height - (start_point.y - ymin)
                is_first_point = False

            if edge.Curve.TypeId in ["Part::GeomLineSegment", "Part::GeomLine"]:
                pdf.line(
                    start_x, start_y, end_point.x - xmin, height - (end_point.y - ymin)
                )
                start_x, start_y = end_point.x - xmin, height - (end_point.y - ymin)
            elif edge.Curve.TypeId in ["Part::GeomCircle", "Part::GeomArcOfCircle"]:
                # Handle circular arc by approximating with line segments
                radius = edge.Curve.Radius
                center = edge.Curve.Center
                start_angle = math.atan2(
                    start_point.y - center.y, start_point.x - center.x
                )
                end_angle = math.atan2(end_point.y - center.y, end_point.x - center.x)

                angle_diff = (end_angle - start_angle) % (2 * math.pi)
                if angle_diff > math.pi:
                    angle_diff -= 2 * math.pi
                elif angle_diff < -math.pi:
                    angle_diff += 2 * math.pi

                num_segments = 20  # Number of segments to approximate the arc
                angle_step = angle_diff / num_segments

                for i in range(num_segments + 1):
                    angle = start_angle + i * angle_step
                    x = center.x + radius * math.cos(angle)
                    y = center.y + radius * math.sin(angle)
                    pdf.line(start_x, start_y, x - xmin, height - (y - ymin))
                    start_x, start_y = x - xmin, height - (y - ymin)

    def calculate_bounding_box(self, sublist):
        xmin, ymin, xmax, ymax = None, None, None, None
        for obj in sublist:
            wires = Path.Geom.wiresForPath(obj.Path)
            for wire in wires:
                for vertex in wire.Vertexes:
                    x, y = vertex.X, vertex.Y
                    if xmin is None or x < xmin:
                        xmin = x
                    if xmax is None or x > xmax:
                        xmax = x
                    if ymin is None or y < ymin:
                        ymin = y
                    if ymax is None or y > ymax:
                        ymax = y
        return xmin, ymin, xmax, ymax

    def get_stroke_style(self, obj):
        strokewidth = 0.1
        color = LAYER_COLORS["DEFAULT"]
        label = None

        if hasattr(obj, "ToolController"):
            tc = obj.ToolController
            if hasattr(tc, "Tool") and hasattr(tc.Tool, "Diameter"):
                strokewidth = tc.Tool.Diameter
            if hasattr(tc, "Label"):
                for key in LAYER_COLORS:
                    if key in tc.Label:
                        label = key
                        color = LAYER_COLORS[key]
                        break

        return {"width": strokewidth, "color": color, "label": label}

    def hex_to_rgb(self, hex_color):
        if hex_color.startswith("#"):
            hex_color = hex_color.lstrip("#")
        else:
            # Default to black if the color is not in hex format
            return 0, 0, 0
        return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

    @property
    def tooltip(self):
        tooltip = """
        This is the Ondsel PDF CAM post processor.
        It will export a CAM job to a PDF file with colors and layers.

        Tool Controllers determine how the PDF will be created and, thus, how the
        laser will behave.  They must have a label containing a string from the list at the top of the post file.
        (e.g. CUT, FILL, ENGRAVE). PDF paths will be color coded similarly

        Actual laser behavior will depend on how the laser controller is configured
        to process the colors / layers.

        Step-downs in operations will result in multiple passes.
        """
        return tooltip

    @property
    def tooltipArgs(self):
        argtooltip = """
        --layers: Output will be written to different layers. Layer names are taken from the operation label
        """
        return argtooltip

    @property
    def preferredExtension(self):
        return "pdf"
