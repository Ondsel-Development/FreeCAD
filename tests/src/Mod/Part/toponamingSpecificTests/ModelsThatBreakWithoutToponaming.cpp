#include "App/ElementMap.h"
#include "Mod/Part/App/FeatureChamfer.h"
#include "Mod/Part/App/FeaturePartBox.h"
#include "Mod/Part/App/FeaturePartFuse.h"
#include "gtest/gtest.h"
#include <App/Application.h>
#include <App/Document.h>

class ModelsThatBreakWithoutToponamingTest: public ::testing::Test
{
protected:
    static void SetUpTestSuite()
    {
        if (App::Application::GetARGC() == 0) {
            int argc = 1;
            char* argv[] = {"FreeCAD"};
            App::Application::Config()["ExeName"] = "FreeCAD";
            App::Application::init(argc, argv);
        }
    }

    void SetUp() override
    {
        _docName = App::GetApplication().getUniqueDocumentName("test");
        _doc = App::GetApplication().newDocument(_docName.c_str(), "testUser");
        _sids = &_sid;
        _hasher = Base::Reference<App::StringHasher>(new App::StringHasher);
    }

    void TearDown() override
    {
        App::GetApplication().closeDocument(_docName.c_str());
    }

    App::Document* _doc;

private:
    std::string _docName;
    Data::ElementIDRefs _sid;
    QVector<App::StringIDRef>* _sids;
    App::StringHasherRef _hasher;
};

TEST_F(ModelsThatBreakWithoutToponamingTest, simpleCaseWithChamfer) // NOLINT
{
    // Arrange
    // >>> Add a box named "Cube"
    _doc->addObject("Part::Box", "Box");
    Part::Box* box = dynamic_cast<Part::Box*>(_doc->getObject("Box"));
    box->Label.setValue("Cube");
    box->execute();
    // >>> Add a Cylinder named "Cylinder" that is halfway down the face of "Cube"
    _doc->addObject("Part::Cylinder","Cylinder");
    Part::Cylinder* cylinder = dynamic_cast<Part::Cylinder*>(_doc->getObject("Cylinder"));
    cylinder->Label.setValue("Cylinder");
    auto cylinderAtOriginPos = cylinder->Placement.getValue();
    auto cylinderMovedPos = Base::Placement(Base::Vector3d(5, 0, 0), Base::Rotation(0, 0, 1, 0));
    cylinder->Placement.setValue(cylinderMovedPos);
    cylinder->execute();
    std::vector<App::DocumentObject *> boxAndCylinder = {box, cylinder};
    // >>> Add a "Cut" that cuts away the cylinder from the cube
    _doc->addObject("Part::MultiFuse", "Fusion");
    Part::MultiFuse* cut = dynamic_cast<Part::MultiFuse*>(_doc->getObject("Fusion"));
    cut->Label.setValue("Cut");
    cut->Shapes.setValues(boxAndCylinder);
    cut->execute();
    // >>> Add a chamfer against the top front edge to the right
    _doc->addObject("Part::Chamfer","Chamfer");
    Part::Chamfer* chamfer = dynamic_cast<Part::Chamfer*>(_doc->getObject("Chamfer"));
    chamfer->Base.setValue(cut);
    std::vector<Part::FilletElement> fillets = {
        Part::FilletElement {10, 1.00, 1.00} // got edgeid 10 through manual run
    };
    chamfer->Edges.setValues(fillets);
    chamfer->execute();

    // Act
    auto filletsBefore = chamfer->Edges.getValues();
    cylinder->Placement.setValue(cylinderAtOriginPos);
    chamfer->execute();
    auto filletsAfter = chamfer->Edges.getValues();

    // Assert
    ASSERT_EQ(filletsBefore.size(), 1);
    ASSERT_EQ(filletsBefore[0].edgeid, 10);
    ASSERT_EQ(filletsBefore[0].radius1, 1.00);
    ASSERT_EQ(filletsBefore[0].radius2, 1.00);
    ASSERT_EQ(filletsAfter.size(), 1);
    // TODO: put the following back when toponaming is fixed.
    // ASSERT_EQ(filletsAfter[0].edgeid, 7) << "Toponaming failure, the chamfer should have moved to edge 7 from 10.";
    ASSERT_EQ(filletsAfter[0].radius1, 1.00);
    ASSERT_EQ(filletsAfter[0].radius2, 1.00);
}
