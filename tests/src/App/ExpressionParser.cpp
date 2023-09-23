#include "App/ElementMap.h"
#include "Mod/Part/App/FeaturePartBox.h"
#include "Mod/Spreadsheet/App/Sheet.h"
#include "gtest/gtest.h"
#include <App/Application.h>
#include <App/Document.h>

class ExpressionParser: public ::testing::Test
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
        _docName = App::GetApplication().getUniqueDocumentName("testDoc");
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

TEST_F(ExpressionParser, basicSpreadsheetCell) // NOLINT
{
    // Arrange
    _doc->addObject("Spreadsheet::Sheet", "Spreadsheet");
    auto* spreadsheet = dynamic_cast<Spreadsheet::Sheet*>(_doc->getObject("Spreadsheet"));
    spreadsheet->setCell("A1", "4");
    _doc->addObject("Part::Box", "Box");
    auto* box = dynamic_cast<Part::Box*>(_doc->getObject("Box"));
    _doc->recompute();

    // Act
    std::shared_ptr<App::Expression> expression(App::Expression::parse(box, "Spreadsheet.A1"));

    // Assert
    EXPECT_EQ(expression.get()->toString(), "Spreadsheet.A1");
}

TEST_F(ExpressionParser, basicDocumentProperty) // NOLINT
{
    // Arrange
    _doc->addObject("Part::Box", "Box");
    auto* box = dynamic_cast<Part::Box*>(_doc->getObject("Box"));
    _doc->recompute();
    auto boxLengthProperty = static_cast<App::PropertyFloat*>(
        _doc->addDynamicProperty("App::PropertyFloat", "box_length")
    );
    boxLengthProperty->setValue(4.0);

    // Act
    auto expression = App::Expression::parse(box, "#box_length");
    std::shared_ptr<App::Expression> sharedExpression(expression);

    // Assert
    auto isDocumentProperty = sharedExpression.get()->getIdentifiers().begin()->first.isDocumentProperty();
    EXPECT_TRUE(isDocumentProperty) << "Parser failed to identify as a document property.";
    EXPECT_EQ(sharedExpression.get()->toString(), "#box_length");
}
