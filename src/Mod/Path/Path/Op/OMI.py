from Path.Dressup.Gui.TagPreferences import HoldingTagPreferences
from PathScripts.PathUtils import waiting_effects
from PySide.QtCore import QT_TRANSLATE_NOOP
import FreeCAD
import Path
import Path.Op.Base as PathOp
import Path.Dressup.Utils as PathDressup
import PathScripts.PathUtils as PathUtils
import copy
import math

# lazily loaded modules
from lazy_loader.lazy_loader import LazyLoader

Part = LazyLoader("Part", globals(), "Part")

translate = FreeCAD.Qt.translate

debug = True

if False:
    Path.Log.setLevel(Path.Log.Level.DEBUG, Path.Log.thisModule())
    Path.Log.trackModule(Path.Log.thisModule())
else:
    Path.Log.setLevel(Path.Log.Level.INFO, Path.Log.thisModule())


class ObjectOMI(PathOp.ObjectOp):
    """
    Proxy object for Probing operation.
    Modified from Probe.py to include probing in non trivial directions.
    The idea for now is to be agnostic of the paths used as basis,
    since idealy we generate a new optimal path for an arbitraty set of probingPoints.
    """

    def opFeatures(self, obj):
        """
        opFeatures(obj) ... Probing works on the stock object.
        """
        #return PathOp.FeatureDepths | PathOp.FeatureHeights | PathOp.FeatureTool #| PathOp.FeatureLocations
        return PathOp.FeatureHeights | PathOp.FeatureTool 

    def initOperation(self, obj):
        obj.addProperty(
            "App::PropertyLinkList",
            "ProbingLocations",
            "OMI",
            QT_TRANSLATE_NOOP("App::Property", "Objects to calculate probing procedure"),
        )
        obj.addProperty(
            "App::PropertyIntegerList",
            "Disabled",
            "OMI",
            QT_TRANSLATE_NOOP("App::Property", "IDs of disabled probing points"),
        )
        obj.addProperty(
            "App::PropertyFloat",
            "ProbingDistance",
            "OMI",
            QT_TRANSLATE_NOOP(
                "App::Property", "Distance between starting and ending positions when probing"
            ),
        )
        obj.addProperty(
            "App::PropertyFile",
            "OutputFileName",
            "Path",
            QT_TRANSLATE_NOOP(
                "App::Property", "The output location for the probe data to be written"
            ),
        )

        self.obj = obj
        obj.Proxy = self

    def cmdProbe(self, obj, probingLocation):
        vf = probingLocation.Point
        v0 = vf + probingLocation.Normal * obj.ProbingDistance
        moveToSafe = Path.Command("G0", {"X": v0.x, "Y": v0.y, 
                                         "Z": obj.ClearanceHeight.Value},
                                  )
        moveToStart = Path.Command("G0", 
                                   {"X": v0.x, "Y": v0.y, "Z": v0.z,},
                                   )
        probingOp = Path.Command("G38.2",
                                 {"X": vf.x, "Y": vf.y, "Z": vf.z,
                                  "F": obj.ToolController.VertFeed.Value,
                                  },
                                 )
        self.commandlist.append(moveToSafe)
        self.commandlist.append(moveToStart)
        self.commandlist.append(probingOp)
        self.commandlist.append(moveToStart)
        self.commandlist.append(moveToSafe)

    def opExecute(self, obj):
        """opExecute(obj) ... generate probe locations."""
        Path.Log.track()
        
        self.commandlist.append(Path.Command("(Begin Probing)"))

        job = PathUtils.findParentJob(obj)
        stock = job.Stock
        bb = stock.Shape.BoundBox

        openstring = "(PROBEOPEN {})".format(obj.OutputFileName)
        self.commandlist.append(Path.Command(openstring))
        self.commandlist.append(Path.Command("G0", {"Z": obj.ClearanceHeight.Value}))

        probeDiameter = obj.ToolController.Tool.Diameter.Value
        for probingLocation in obj.ProbingLocations:
            probingLocation.Proxy.setVectors(probeDiameter)
            self.cmdProbe(obj, probingLocation)
            #probingLocation.Proxy.execute(probingLocation)

        self.commandlist.append(Path.Command("(PROBECLOSE)"))

    def addProbingLocation(self, obj, reference, location):
        job = PathUtils.findParentJob(obj)
        
        probingOp = obj.Document.addObject("App::FeaturePython", "ProbingOp")
        if reference in job.Operations.Group:
            proxy = ProbingToolOp(probingOp, reference, location)
        else:
            proxy = ProbingOp(probingOp, reference, location)
        probingOp.ViewObject.Proxy = 0
        
        probingLocations = obj.ProbingLocations
        probingLocations.append(probingOp)
        obj.ProbingLocations = probingLocations
        #obj.recompute()
        #return probingOp

    def opOnChanged(self, obj, prop):
        print("Change property: " + str(obj.Name) + " " + str(prop))
        #for pL in obj.ProbingLocations:
        #    pL.recompute()

def isPointOnEdge(pt, edge):
    param = edge.Curve.parameter(pt)
    if edge.FirstParameter <= param <= edge.LastParameter:
        return True
    if edge.LastParameter <= param <= edge.FirstParameter:
        return True
    if Path.Geom.isRoughly(edge.FirstParameter, param) or Path.Geom.isRoughly(
        edge.LastParameter, param
    ):
        return True
    return False

class ProbingOp:
    """Base class in case a viewProvider is given to the probing points."""
    def __init__(self, obj, reference, location):
        obj.addProperty(
            "App::PropertyLink",
            "Reference",
            "ProbingOp",
            QT_TRANSLATE_NOOP("App::Property", "Reference object"),
        )
        obj.addProperty(
            "App::PropertyVector",
            "AnchorPoint",
            "ProbingOp",
            QT_TRANSLATE_NOOP("App::Property", "Point in the Reference surface"),
        )
        obj.addProperty(
            "App::PropertyVector",
            "Point",
            "ProbingOp",
            QT_TRANSLATE_NOOP("App::Property", "Probing Point"),
        )
        obj.addProperty(
            "App::PropertyVector",
            "Normal",
            "ProbingOp",
            QT_TRANSLATE_NOOP("App::Property", "Normal vector at probing point"),
        )

        obj.Proxy = self
        self.obj = obj
       
        obj.Reference = reference
        self.setAnchorPoint(location)

    def execute(self, fp):
        ''' Print a short message when doing a recomputation, this method is mandatory '''
        pass

    def onBeforeChange(self, fp, prop):
        print("onBeforeChange", fp.Name, prop)

    def setAnchorPoint(self, point):
        fp = self.obj
        fp.AnchorPoint = point

    def setVectors(self, probeDiameter):
        """Assumes spherical probe, otherwise, change this method."""
        fp = self.obj
        normal = FreeCAD.Vector(0,0,0)
        
        for face in fp.Reference.Shape.Faces:
            u, v = face.Surface.parameter(fp.AnchorPoint)
            projPoint = face.valueAt(u, v)
            distance = fp.AnchorPoint.distanceToPoint(projPoint)
            if Path.Geom.isRoughly(distance, 0):
                normal += face.normalAt(u, v)

        fp.Normal = normal.normalize() 
        fp.Point = fp.AnchorPoint + fp.Normal * probeDiameter/2
    
class ProbingToolOp(ProbingOp):
    def __init__(self, obj, reference, location):
        obj.addProperty(
            "App::PropertyLinkList",
            "RefModels",
            "ProbingOp",
            QT_TRANSLATE_NOOP("App::Property", "Reference model list"),
        )
        obj.addProperty(
            "Part::PropertyPartShape",
            "ToolShape",
            "ProbingOp",
            QT_TRANSLATE_NOOP("Part::Property", "Tool shape"),
        )
        obj.addProperty(
            "App::PropertyVector",
            "ProfileNormal",
            "ProbingOp",
            QT_TRANSLATE_NOOP("App::Property", "Tool profile normal"),
        )
        obj.addProperty(
            "Part::PropertyPartShape",
            "AllowedRegion",
            "ProbingOp",
            QT_TRANSLATE_NOOP("Part::Property", "Allowed region for allocation of probing point"),
        )
        obj.addProperty(
            "Part::PropertyPartShape",
            "RefShape",
            "ProbingOp",
            QT_TRANSLATE_NOOP("Part::Property", "Reference shape obtained from reference"),
        )

        job = PathUtils.findParentJob(reference)
        path = reference.Path
        #Maybe remove the G0's from path first to have a clean probing refShape?
        wire, _ = Path.Geom.wireForPath(path)
        obj.RefModels = job.Model.Group
        obj.ToolShape = reference.ToolController.Tool.Shape
        obj.RefShape = wire
        
        super().__init__(obj, reference, location)

    def setAnchorPoint(self, point, tol = 1e-2):
        # Missing concavity check and correction
        Path.Log.track()
        fp = self.obj
        fp.AnchorPoint = point
        probingPoints = []
        origin = FreeCAD.Vector(0, 0, 0)
        zDir = FreeCAD.Vector(0, 0, 1)
        if not fp.RefShape.isInside(point, tol, False):
            raise ValueError(f'Point {point} outside the path {fp.Reference} for tol={tol}.')
        else: 
            fp.ToolShape = fp.ToolShape.translated(point)
            validEdge = None
            for edge in fp.RefShape.Edges:
                if isPointOnEdge(point, edge):
                    validEdge = edge
                    continue
            
            param = validEdge.Curve.parameter(point)
            tangent = validEdge.tangentAt(param)

            if tangent.cross(zDir) == origin: 
                distMin = None
                vectorsMin = None
                for model in fp.RefModels:
                    dist, vectors, _ = fp.ToolShape.distToShape(model.Shape)
                    if distMin is None or distMin > dist:
                        distMin = dist
                        vectorsMin = vectors

                for pair in vectorsMin:
                    v = pair[0]
                    dx = v - point
                    if not Path.Geom.isRoughly(dx.Length, 0):
                        tangent = dx.cross(zDir)
                        continue

            profileNormal = tangent.projectToPlane(origin, zDir)
            fp.ProfileNormal = profileNormal.normalize()
        
    def setAllowedRegion(self, probeDiameter):
        """
        Assumes spherical probe, otherwise, change this method.
        May want to add more constrains in the future, like removing not useful edges.
        """
        fp = self.obj
        toolShape = fp.ToolShape.translated(-fp.AnchorPoint)
        toolProfile = toolShape.slice(fp.ProfileNormal, 0)[0]
        #Need to do something else when probeDia > toolDia
        # makeOffset2D(offset, join = (0, 1, or 2), fill = False, openResult = False, intersection = False)
        allowedRegion = toolProfile.makeOffset2D(-probeDiameter/2, intersection = True)
        fp.AllowedRegion = allowedRegion.translated(fp.AnchorPoint)
        #region = FreeCAD.ActiveDocument.addObject("Part::Feature", "Region")
        #region.Shape = fp.AllowedRegion

    def setVectors(self, probeDiameter, tol = 1e-4):
        fp = self.obj
        self.setAllowedRegion(probeDiameter)
        if fp.Point == FreeCAD.Vector(0,0,0):
            distMin = None
            for model in fp.RefModels:
                dist, vectors, info = fp.AllowedRegion.distToShape(model.Shape)
                if distMin is None or dist < distMin:
                    distMin = dist
                    fp.Point = vectors[0][0]
                    normal = fp.Point - vectors[0][1]
                    fp.Normal = normal.normalize()
        elif fp.AllowedRegion.isInside(fp.Point, tol, False):
            for edge in fp.AllowedRegion.Edges:
                param = edge.Curve.parameter(fp.Point)
                if isPointOnEdge(fp.Point, edge):
                    tan = edge.tangentAt(param)
                    print('second conditional in setVectors')
                    print(tan)
                    #normal = tan.cross(fp.ProfileNormal)
                    normal = fp.ProfileNormal.cross(tan)
                    fp.Normal = normal.normalize()
                    #continue
        else:
            fp.Point = FreeCAD.Vector(0,0,0)
            self.setVectors(probeDiameter, tol)

def Create(name, obj=None, parentJob=None):
   """Create(name) ... Creates and returns a Probing operation."""
   if obj is None:
       obj = FreeCAD.ActiveDocument.addObject("Path::FeaturePython", name)
   proxy = ObjectOMI(obj, name, parentJob)
   return obj

def SetupProperties():
    # setup = ["Xoffset", "Yoffset", "PointCountX", "PointCountY", "OutputFileName"]
    setup = ["ProbingLocations", "ToolController", "OutputFileName"]
    return setup
