#include "Mod/Part/App/FeaturePartFuse.h"
#include "App/ElementMap.h"
#include "Mod/Part/App/FeaturePartBox.h"
#include "gtest/gtest.h"
#include <App/Application.h>
#include <App/Document.h>

class FeaturePartFuseTest: public ::testing::Test
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

TEST_F(FeaturePartFuseTest, simpleBoxCylinderFusionHistory) // NOLINT
{
    // Arrange
    _doc->addObject("Part::Box", "Box");
    Part::Box* box = dynamic_cast<Part::Box*>(_doc->getObject("Box"));
    box->execute();
    _doc->addObject("Part::Cylinder","Cylinder");
    Part::Cylinder* cylinder = dynamic_cast<Part::Cylinder*>(_doc->getObject("Cylinder"));
    cylinder->execute();

    // Act
    _doc->addObject("Part::MultiFuse", "Fusion");
    Part::MultiFuse* fusion = dynamic_cast<Part::MultiFuse*>(_doc->getObject("Fusion"));
    std::vector<App::DocumentObject *> x = {box, cylinder};
    auto historySizeBefore = fusion->History.getSize();
    fusion->Shapes.setValues(x);
    fusion->execute();
    auto historySizeAfter = fusion->History.getSize();

    // Assert
    ASSERT_EQ(historySizeBefore, 0);
    ASSERT_EQ(historySizeAfter, 2);
}
