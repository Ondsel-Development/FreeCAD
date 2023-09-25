#include "Mod/Part/App/FeaturePartBox.h"
#include "Mod/Spreadsheet/App/Sheet.h"
#include "gtest/gtest.h"
#include <App/Application.h>
#include <App/Document.h>

class DocumentExpression: public ::testing::Test
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
        _otherDocName = App::GetApplication().getUniqueDocumentName("otherDoc");
        _otherDoc = App::GetApplication().newDocument(_otherDocName.c_str(), "otherUser");
    }

    void TearDown() override
    {
        App::GetApplication().closeDocument(_docName.c_str());
        App::GetApplication().closeDocument(_otherDocName.c_str());
    }

    App::Document* _doc;
    App::Document* _otherDoc;

private:
    std::string _docName;
    std::string _otherDocName;
};

TEST_F(DocumentExpression, spreadsheetBinding) // NOLINT
{
    // Arrange
    // >>> Add a 10mm x 10mm x 10mm box named "Cube"
    _doc->addObject("Part::Box", "Box");
    auto* box = dynamic_cast<Part::Box*>(_doc->getObject("Box"));
    box->Label.setValue("Cube");
    box->execute();
    auto boxLengthOid = App::ObjectIdentifier::parse(box, "Length");
    // >>> Add spreadsheet and set A1 to 4
    _doc->addObject("Spreadsheet::Sheet", "Spreadsheet");
    auto* spreadsheet = dynamic_cast<Spreadsheet::Sheet*>(_doc->getObject("Spreadsheet"));
    spreadsheet->setCell("A1", "4");
    _doc->recompute();

    // Act
    std::shared_ptr<App::Expression> expression(App::Expression::parse(box, "Spreadsheet.A1"));
    box->setExpression(
        boxLengthOid,
        expression
    );
    _doc->recompute();

    // Assert
    auto expressionDetailOnBox = box->getExpression(boxLengthOid).expression.get()->toString();
    EXPECT_EQ(expressionDetailOnBox, "Spreadsheet.A1");
    std::string a1Content;
    spreadsheet->getCell(App::stringToAddress("A1"))->getStringContent(a1Content);
    EXPECT_EQ(a1Content, "4");
    auto length = box->Length.getValue();
    EXPECT_EQ(length, 4.0);
}

// this does not work yet as it appears to expect an external file, not simply a second document
// on the same application.
//TEST_F(DocumentExpression, externalDocumentPropertiesBinding) // NOLINT
//{
//    // Arrange
//    // >>> Add a box named "Cube1" to main doc with default length of 10.0
//    _doc->addObject("Part::Box", "Cube1");
//    auto* box = dynamic_cast<Part::Box*>(_doc->getObject("Cube1"));
//    box->execute();
//    auto boxLengthOid = App::ObjectIdentifier::parse(box, "Length");
//    // >>> Add a box named "Cube2" to "otherDoc" that has a Length of 4.0
//    _otherDoc->addObject("Part::Box", "Cube2");
//    auto* otherBox = dynamic_cast<Part::Box*>(_otherDoc->getObject("Cube2"));
//    otherBox->Length.setValue(4.0);
//    otherBox->execute();
//
//    // Act
//    std::shared_ptr<App::Expression> expression(App::Expression::parse(box, "otherDoc#Cube2.Length"));
//    box->setExpression(
//        boxLengthOid,
//        expression
//    );
//    _doc->recompute();
//
//    // Assert
//    auto actualBoxLength = box->Length.getValue();
//    EXPECT_EQ(actualBoxLength, 4.0);
//}

TEST_F(DocumentExpression, currentDocumentPropertiesBinding) // NOLINT
{
    // Arrange
    // >>> Add a box named "Cube"
    _doc->addObject("Part::Box", "Box");
    auto* box = dynamic_cast<Part::Box*>(_doc->getObject("Box"));
    box->Label.setValue("Cube");
    box->execute();
    auto boxLengthOid = App::ObjectIdentifier::parse(box, "Length");
    // >>> Set custom property to current document called "box_length"; set to 4.0
    auto boxLengthProperty = static_cast<App::PropertyFloat*>(
        _doc->addDynamicProperty("App::PropertyFloat", "box_length")
    );
    boxLengthProperty->setValue(4.0);

    // Act
    std::shared_ptr<App::Expression> expression(App::Expression::parse(box, "#box_length"));
    box->setExpression(
        boxLengthOid,
        expression
    );
    _doc->recompute();

    // Assert
    auto expressionDetailOnBox = box->getExpression(boxLengthOid).expression.get()->toString();
    EXPECT_EQ(expressionDetailOnBox, "#box_length");
    auto docBoxLengthProp = static_cast<App::PropertyFloat*>(
        _doc->getPropertyByName("box_length")
    );
    EXPECT_EQ(docBoxLengthProp->getValue(), 4.0);
    auto actualBoxLength = box->Length.getValue();
    EXPECT_EQ(actualBoxLength, 4.0);
}
