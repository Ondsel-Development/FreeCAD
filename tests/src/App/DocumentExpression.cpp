#include "App/ElementMap.h"
#include "Mod/Part/App/FeaturePartBox.h"
#include "Mod/Spreadsheet/App/Sheet.h"
#include "gtest/gtest.h"
#include <App/Application.h>
#include <App/Document.h>

/*
 In summary, this class will test that the following combinations work:

    $a#k.Width  = from doc a, get object k's property Width
    $a.d        = from doc a, get document-property d
    $#k.Width   = from current doc, get object k's property Width
    $.d         = from current doc, get document-property d
    #k.Width    = from current doc, get object k's property Width
    k.Width     = from current doc, get object k's property Width
    #.Height    = from current doc, from current object, get property Height
    .Height     = from current doc, from current object, get property Height (legacy behavior)

 It will also test that the following combinations will NOT work:

    #u    = this is an object in the current doc, what should be returned?
    $a    = this is doc a, what should be returned?
    $     = this is the current doc, what should be returned?
    #     = this is the current object on the current doc, what should be returned?
    #$.i  = out of order; makes no sense
    $.#   = out of order; makes no sense
*/

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
        // >> create two Documents: "a" and "b"
        _aDocName = App::GetApplication().getUniqueDocumentName("a");
        _aDoc = App::GetApplication().newDocument(_aDocName.c_str(), "testUser");
        _bDocName = App::GetApplication().getUniqueDocumentName("b");
        _bDoc = App::GetApplication().newDocument(_bDocName.c_str(), "testUser");
        _sids = &_sid;
        _hasher = Base::Reference<App::StringHasher>(new App::StringHasher);
        // >>> On doc "a", set a property called "d" to 4.0
        auto boxLengthProperty = static_cast<App::PropertyFloat*>(
            _aDoc->addDynamicProperty("App::PropertyFloat", "d")
        );
        boxLengthProperty->setValue(4.0);
        // >>> Add a cube named "target" with default Length/Width of 10, but Height of 7.0
        _aDoc->addObject("Part::Box", "Box");
        _targetCube = dynamic_cast<Part::Box*>(_aDoc->getObject("Box"));
        _targetCube->Label.setValue("target");
        _targetCube->Height.setValue(7.0);
        _targetCube->execute();
        // >>> Add a cube named "k" with Width 5.0
        _aDoc->addObject("Part::Box", "Box");
        _kCube = dynamic_cast<Part::Box*>(_aDoc->getObject("Box"));
        _kCube->Label.setValue("k");
        _kCube->Width.setValue(5.0);
        _kCube->execute();
    }

    void TearDown() override
    {
        App::GetApplication().closeDocument(_aDocName.c_str());
        App::GetApplication().closeDocument(_bDocName.c_str());
    }

protected:
    std::string _aDocName;
    App::Document* _aDoc;
    std::string _bDocName;
    App::Document* _bDoc;
    Part::Box* _targetCube;
    Part::Box* _kCube;

private:
    Data::ElementIDRefs _sid;
    QVector<App::StringIDRef>* _sids{};
    App::StringHasherRef _hasher;
};


// binding cube k's length to expression: Spreadsheet.A1
TEST_F(DocumentExpression, spreadsheetBinding) // NOLINT
{
    // Arrange
    // >>> Add spreadsheet and set A1 to 4
    _aDoc->addObject("Spreadsheet::Sheet", "Spreadsheet");
    auto* spreadsheet = dynamic_cast<Spreadsheet::Sheet*>(_aDoc->getObject("Spreadsheet"));
    spreadsheet->setCell("A1", "4");
    _bDoc->recompute();

    // Act
    std::shared_ptr<App::Expression> expression(App::Expression::parse(_targetCube, "Spreadsheet.A1"));
    _targetCube->setExpression(
        App::ObjectIdentifier::parse(_targetCube, "Length"),
        expression
    );
    _aDoc->recompute();

    // Assert
    std::string a1Content;
    spreadsheet->getCell(App::stringToAddress("A1"))->getStringContent(a1Content);
    EXPECT_EQ(a1Content, "4");
    auto length = _targetCube->Length.getValue();
    EXPECT_EQ(length, 4.0);
}

// $a#k.Width  = from doc a, get object k's property Width
TEST_F(DocumentExpression, documentPropertiesBinding_dol_a_pound_k_dot_Width) // NOLINT
{
    // Arrange (arranged in Setup)
    // cube "k" has a width of 5.0

    // Act
    std::shared_ptr<App::Expression> expression(App::Expression::parse(_targetCube, "$a#k.Width"));
    _targetCube->setExpression(
        App::ObjectIdentifier::parse(_targetCube, "Length"),
        std::shared_ptr<App::Expression>(expression)
    );
    _aDoc->recompute();

    // Assert
    EXPECT_EQ(expression->toString(), "$a#k.Width");
    auto actualBoxLength = _targetCube->Length.getValue();
    EXPECT_EQ(actualBoxLength, 5.0);
}

// $a.d        = from doc a, get document-property d
TEST_F(DocumentExpression, documentPropertiesBinding_dol_a_dot_d) // NOLINT
{
    // Arrange (arranged in Setup)
    // document "a" has a document-property "d" of 4.0

    // Act
    std::shared_ptr<App::Expression> expression(App::Expression::parse(_targetCube, "$a.d"));
    _targetCube->setExpression(
        App::ObjectIdentifier::parse(_targetCube, "Length"),
        expression
    );
    _aDoc->recompute();

    // Assert
    EXPECT_EQ(expression->toString(), "$a.d");
    auto docBoxLengthProp = dynamic_cast<App::PropertyFloat*>(
        _aDoc->getPropertyByName("d")
    );
    EXPECT_EQ(docBoxLengthProp->getValue(), 4.0);
    auto actualBoxLength = _targetCube->Length.getValue();
    EXPECT_EQ(actualBoxLength, 4.0);
}

// $#k.Width   = from current doc, get object k's property Width
TEST_F(DocumentExpression, documentPropertiesBinding_dol_pound_k_dot_Width) // NOLINT
{
    // Arrange (arranged in Setup)
    // cube "k" has a width of 5.0

    // Act
    std::shared_ptr<App::Expression> expression(App::Expression::parse(_targetCube, "$#k.Width"));
    _targetCube->setExpression(
        App::ObjectIdentifier::parse(_targetCube, "Length"),
        std::shared_ptr<App::Expression>(expression)
    );
    _aDoc->recompute();

    // Assert
    EXPECT_EQ(expression->toString(), "$#k.Width");
    auto actualBoxLength = _targetCube->Length.getValue();
    EXPECT_EQ(actualBoxLength, 5.0);
}

// $.d         = from current doc, get document-property d
TEST_F(DocumentExpression, documentPropertiesBinding_dol_dot_d) // NOLINT
{
    // Arrange (arranged in Setup)
    // current document "a" has a document-property "d" of 4.0

    // Act
    std::shared_ptr<App::Expression> expression(App::Expression::parse(_targetCube, "$.d"));
    _targetCube->setExpression(
        App::ObjectIdentifier::parse(_targetCube, "Length"),
        expression
    );
    _aDoc->recompute();

    // Assert
    EXPECT_EQ(expression->toString(), "$.d");
    auto docBoxLengthProp = dynamic_cast<App::PropertyFloat*>(
        _aDoc->getPropertyByName("d")
    );
    EXPECT_EQ(docBoxLengthProp->getValue(), 4.0);
    auto actualBoxLength = _targetCube->Length.getValue();
    EXPECT_EQ(actualBoxLength, 4.0);
}

// #k.Width    = from current doc, get object k's property Width
TEST_F(DocumentExpression, documentPropertiesBinding_pound_k_dot_Width) // NOLINT
{
    // Arrange (arranged in Setup)
    // cube "k" has a width of 5.0

    // Act
    std::shared_ptr<App::Expression> expression(App::Expression::parse(_targetCube, "#k.Width"));
    _targetCube->setExpression(
        App::ObjectIdentifier::parse(_targetCube, "Length"),
        std::shared_ptr<App::Expression>(expression)
    );
    _aDoc->recompute();

    // Assert
    EXPECT_EQ(expression->toString(), "#k.Width");
    auto actualBoxLength = _targetCube->Length.getValue();
    EXPECT_EQ(actualBoxLength, 5.0);
}

// k.Width     = from current doc, get object k's property Width
TEST_F(DocumentExpression, documentPropertiesBinding_k_dot_Width) // NOLINT
{
    // Arrange (arranged in Setup)
    // in the current doc "a", cube "k" has a Width of 5.0

    // Act
    std::shared_ptr<App::Expression> expression(App::Expression::parse(_targetCube, "k.Width"));
    _targetCube->setExpression(
        App::ObjectIdentifier::parse(_targetCube, "Length"),
        expression
    );
    _aDoc->recompute();

    // Assert
    EXPECT_EQ(expression->toString(), "Width");
    auto actualBoxLength = _targetCube->Length.getValue();
    EXPECT_EQ(actualBoxLength, 5.0);
}

// #.Height    = from current doc, from current object, get property Height
TEST_F(DocumentExpression, documentPropertiesBinding_pound_dot_Height) // NOLINT
{
    // Arrange (arranged in Setup)
    // cube "target" has it's own Height of 7.0
    // we are setting the Width (was 10.0) of same object to it's Height

    // Act
    std::shared_ptr<App::Expression> expression(App::Expression::parse(_targetCube, "#.Height"));
    _targetCube->setExpression(
        App::ObjectIdentifier::parse(_targetCube, "Length"),
        expression
    );
    _aDoc->recompute();

    // Assert
    EXPECT_EQ(expression->toString(), ".Height");
    auto actualBoxLength = _targetCube->Length.getValue();
    EXPECT_EQ(actualBoxLength, 7.0);
}

// .Height     = from current doc, from current object, get property c (legacy behavior)
TEST_F(DocumentExpression, documentPropertiesBinding_dot_Height) // NOLINT
{
    // Arrange (arranged in Setup)
    // cube "target" has it's own Height of 7.0
    // we are setting the Width (was 10.0) of same object to it's Height

    // Act
    std::shared_ptr<App::Expression> expression(App::Expression::parse(_targetCube, ".Height"));
    _targetCube->setExpression(
        App::ObjectIdentifier::parse(_targetCube, "Length"),
        expression
    );
    _aDoc->recompute();

    // Assert
    EXPECT_EQ(expression->toString(), ".Height");
    auto actualBoxLength = _targetCube->Length.getValue();
    EXPECT_EQ(actualBoxLength, 7.0);
}
