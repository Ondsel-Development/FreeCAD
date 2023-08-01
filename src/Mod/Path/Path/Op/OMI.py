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
        return PathOp.FeatureDepths | PathOp.FeatureHeights | PathOp.FeatureTool

    def initOperation(self, obj):
        #obj.addProperty(
        #    "App::PropertyLink",
        #    "Base",
        #    "Path",
        #    QT_TRANSLATE_NOOP("App::Property", "The base geometry to use as reference"),
        #)
        obj.addProperty(
            "App::PropertyVectorList",
            "Starts",
            "Probe",
            QT_TRANSLATE_NOOP("App::Property", "Starting probing locations"),
        )
        obj.addProperty(
            "App::PropertyVectorList",
            "Ends",
            "Probe",
            QT_TRANSLATE_NOOP("App::Property", "Ending probing locations"),
        )
        obj.addProperty(
            "App::PropertyIntegerList",
            "Disabled",
            "OMI",
            QT_TRANSLATE_NOOP("App::Property", "IDs of disabled probing points"),
        )
        obj.addProperty(
            "App::PropertyInteger",
            "PointCount",
            "Probe",
            QT_TRANSLATE_NOOP(
                "App::Property", "Number of points to probe (counting disabled)"
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
        obj.addProperty(
            "App::PropertyFloat",
            "ProbeRadius",
            "OMI",
            QT_TRANSLATE_NOOP(
                "App::Property", "The radius of the spherical probe tool"
            ),
        )

        self.addBaseProperty(obj)
        self.obj = obj
        self.models = None
        self.pathData = None
        self.ProbeRadius = None
        obj.Proxy = self

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        self.obj = state
        self.pathData = None
        self.probeRadius = None
        return None

    def onDocumentRestored(self, obj):
        self.obj = obj

    def cmdProbe(self, v0, vf):
        self.commandlist.append(
            Path.Command(
                "G0",
                {
                    "X": v0.x,
                    "Y": v0.y,
                    "Z": v0.z,
                },
            )
        )
        self.commandlist.append(
            Path.Command(
                "G38.2",
                {
                    "X": vf.x,
                    "Y": vf.y,
                    "Z": vf.z,
                    "F": ToolController.VertFeed.Value,
                },
            )
        )
        self.commandlist.append(
            Path.Command(
                "G0",
                {
                    "X": v0.x,
                    "Y": v0.y,
                    "Z": v0.z,
                },
            )
        )

    def opExecute(self, obj):
        """opExecute(obj) ... generate probe locations."""
        Path.Log.track()

        doLengthsMatch = obj.PointCount == len(obj.Starts) == len(obj.Ends)
        if not doLengthsMatch:
            Path.Log.debug('Lists Lenghts and probing point count do not match.')
            return

        self.commandlist.append(Path.Command("(Begin Probing)"))

        stock = PathUtils.findParentJob(obj).Stock
        bb = stock.Shape.BoundBox

        openstring = "(PROBEOPEN {})".format(obj.OutputFileName)
        self.commandlist.append(Path.Command(openstring))
        self.commandlist.append(Path.Command("G0", {"Z": obj.ClearanceHeight.Value}))

        for i in range(obj.PointCount):
            if i not in obj.Disabled:
                v0 = obj.Starts[i]
                vf = obj.Ends[i]
                self.cmdProbe(v0, vf)

        self.commandlist.append(Path.Command("(PROBECLOSE)"))

    def generateProbingPoints(self, obj):
        probingPoints = self.pathData.generateProbingPoints()
        for probing in probingPoints:
            v0, vf = probing.createProbingPoint()
            obj.Starts.append(v0)
            obj.Ends.append(vf)
        #obj.Disabled.append([i + obj.PointCount for i in newDisabled])
        obj.PointCount = len(obj.Starts)    
        #obj.Disabled = []
     
    def setup(self, obj, base, generate = False):
        Path.Log.debug('setup')
        job = PathUtils.findParentJob(base)
        self.obj = obj
        self.job = job
        self.models = job.Model.Group

        try:
            pathData = PathData(base)
            pathData.setOffsetWire(self.ProbeRadius)
        except ValueError:
            Path.Log.error(
                translate(
                    "Path_OMI",
                    "Cannot generate probing points for this path - please select a Profile path",
                    )
                + "\n"
                )
            return None
        
        self.pathData = pathData
        if generate:
            self.generateProbingPoints(obj)

        return self.pathData
    
class PathData:
    def __init__(self, obj):
        Path.Log.track(obj.Name)
        job = PathUtils.findParentJob(obj)
        self.obj = obj
        self.models = job.Model.Group
        
        faces = []
        for model in self.models:
            faces += model.Shape.Faces
        self.faces = faces

        path = PathUtils.getPathWithPlacement(obj)
        self.wire, rapid = Path.Geom.wireForPath(path)
        if self.wire:
            self.edges = self.wire.Edges
        else:
            self.edges = []

        tc = PathDressup.toolController(obj)
        tool = tc.Tool
        self.toolShape = tool.Shape
        self.toolEdges = []
        self.cuttingEdgeHeight = tool.CuttingEdgeHeight
        self.toolEdgeNormal = FreeCAD.Vector(0,1,0)
        self.toolWire = tool.Shape.slice(self.toolEdgeNormal, 0)[0]
        self.probeRadius = None
        self.offsetWire = None
        self.activePath = None
        # How do we remove the tool shank?
        #for w in tool.Shape.slice(self.toolEdgeNormal, 0):
        #   for edge in w.Edges:
        #       if all([v.Z <= CuttingEdgeHeight for v in edge.Vertexes]):
        #           self.toolEdges.append(edge)

    def setOffsetWire(self, probeRadius):
        self.probeRadius = probeRadius
        self.offsetWire = self.toolWire.makeOffset2D(-probeRadius)
    
    def generateProbingPoints(self):
        # Missing concavity check and correction
        Path.Log.track()
        probingPoints = []
        origin = FreeCAD.Vector(0,0,0)
        z_dir  = FreeCAD.Vector(0,0,1)

        for i, edge in enumerate(self.edges):
            Path.Log.debug(f"{i}")
            # For now only one point at middle of edge
            param = 0.5 * (edge.LastParameter + edge.FirstParameter)
            pt = edge.Curve.value(param)
            tangent = edge.tangentAt(param)

            if tangent.cross(z_dir) == origin: # Tangent vector of path in z direction, not good
                # We find the closest face of the original shape and 
                # project our point to get a direction
                '''
                closestFace = None
                lowerDistance = None
                for face in self.faces:
                    #vertexes = edge.common(solid).Vertexes
                    #if vertexes:
                    #    pt = sorted(vertexes, key=lambda v: (v.Point - refPt).Length)[0].Point
                    
                    #d = face.Surface.projectPoint(point, "LowerDistance") #is the use of Surface correct here?
                    if closestFace is None or d < lowerDistance:
                        closestFace = face
                        lowerDistance = d
                tangent = z_dir.cross(closestFace.Surface.projectPoint(pt))
                '''
                toolAtPoint = self.toolShape.translated(pt)
                dist_min = None
                tangent = None
                for model in self.models:
                    dist, vectors, _ = model.Shape.distToShape(toolAtPoint)
                    if dist_min is None or dist_min > dist:
                        dist_min = dist
                        for pair in vectors:
                            v = pair[1]
                            if not v.isEqual(pt, 1e-5):
                                tangent = pt - v
                                continue

            tangent_XY = tangent.projectToPlane(origin, z_dir)
            phi = tangent_XY.getAngle(self.toolEdgeNormal) # relative angle on XY plane
            toolWire = self.toolWire.rotate(origin, z_dir, phi).translate(pt)
            offsetWire = self.offsetWire.rotate(origin, z_dir, phi).translate(pt)
            innerRegion = Part.Face(offsetWire)
            
            activePath = []
            for edge in offsetWire.Edges:
                distances = []
                for model in self.models:
                    """
                    for pair in vectors:
                        v = pair[0].sub(pair[1]).normalize()
                        v *= .05 #5 percent displacement
                        if not innerRegion.isInside(pair[0] + v, 1e-6, True):
                            if all([v.Z <= self.cuttingEdgeHeight for v in edge.Vertexes]):
                                activePath.append(edge)
                    """
                    d, _ , _ = edge.distToShape(model.Shape)
                    distances.append(d)
                activePath.append(min(distances))
            
            distMin = min(activePath)
            #activePath = [d <= distMin for d in activePath]
            activePath = [edge for edge, d in zip(offsetWire.Edges, activePath) 
                          if Path.Geom.isRoughly(d, distMin)]
            '''
            distToShape = [e.distToShape(obj.Base.Base.Shape)[0] for e in toolWire.Edges]
            dMin = min(distToShape)
            # Only keep the closest edges to the object.
            toolEdges = []
            for (d, e) in zip(distToShape, displacedToolEdges):
                if Path.Geom.isRoughly(d, dMin):
                    toolEdges.append(e)
            '''

            probingPoints.append(
                    ProbingPoint(pt, tangent_XY, self.probeRadius, toolWire, activePath)
                    )

        return probingPoints


class ProbingPoint:
    def __init__(self, pt, normal, probeRadius, toolWire, activePath, enabled = True):
        Path.Log.track(f'{pt.x, pt.y, pt.z, probeRadius, enabled}')
        self.pt = pt
        self.surfaceNormal = normal
        self.probeRadius = probeRadius
        self.probingDistance = 2 * probeRadius
        self.toolWire = toolWire
        self.activePath = activePath
        self.parameterRange = []
        for edge in self.activePath:
            self.parameterRange.append(edge.FirstParameter)
            self.parameterRange.append(edge.LastParameter)
        self.enabled = enabled
        
        self.v0 = None
        self.vf = None

    def setProbingDistance(self, distance):
        self.probingDistance = distance

    @staticmethod
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

    def normalOnPath(self, pt):
        #Doesnt work
        totalTangent = FreeCAD.Vector(0,0,0)
        for edge in self.activePath:
            param = edge.Curve.parameter(pt)
            if ProbingPoint.isPointOnEdge(pt, edge):
                tan = edge.tangentAt(param)
                totalTangent += tan
        v = totalTangent.cross(self.surfaceNormal)
        v = v.normalize()

        return v

    def isPointOnPath(self, pt):
        for edge in self.activePath:
            if ProbingPoint.isPointOnEdge(pt, edge):
                return True
        return False

    def createProbingPoint(self, pt = None):
        if pt is None:
            pt = self.pt
        if self.isPointOnPath(pt):
            normal = self.normalOnPath(pt)
            self.v0 = pt - normal * self.probingDistance            
            self.vf = pt
        return self.v0, self.vf    
            

#def Create(name, obj=None, parentJob=None):
#    """Create(name) ... Creates and returns a Probing operation."""
#    if obj is None:
#        obj = FreeCAD.ActiveDocument.addObject("Path::FeaturePython", name)
#    proxy = ObjectProbing(obj, name, parentJob)
#    return obj


def Create(baseObject, name="OMI"):
    """
    Create(basePath, name='OMI') ... create OMI object for the given base path.
    """
    if (not baseObject.isDerivedFrom("Path::Feature")
        and not baseObject.isDerivedFrom("Path::FeatureCompoundPython")):
        Path.Log.error(
            translate("Path_OMI", "The selected object is not a path") + "\n"
        )
        return None

    obj = FreeCAD.ActiveDocument.addObject("Path::FeaturePython", name)
    #print(baseObject.Base)
    job = PathUtils.findParentJob(baseObject)
    dbo = ObjectOMI(obj, name, parentJob = job)# parameter?
    obj.Proxy = dbo
    dbo.ProbeRadius = 2. #To be replaced with proper ToolController
    job.Proxy.addOperation(obj, baseObject)
    
    dbo.setup(obj, baseObject, True)
    return obj

for obj in Gui.Selection.getSelection():
    omi = Create(obj)
    #omi.Proxy.execute(omi)
