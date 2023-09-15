#include "App/ElementMap.h"
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

TEST_F(DocumentExpression, spreadsheetBinding) // NOLINT
{
    // Arrange
    // >>> Add a box named "Cube"
    _doc->addObject("Part::Box", "Box");
    auto* box = dynamic_cast<Part::Box*>(_doc->getObject("Box"));
    box->Label.setValue("Cube");
    box->execute();

    // >>> Add spreadsheet and set A1 to 4
    _doc->addObject("Spreadsheet::Sheet", "Spreadsheet");
    auto* spreadsheet = dynamic_cast<Spreadsheet::Sheet*>(_doc->getObject("Spreadsheet"));
    spreadsheet->setCell("A1", "4");
    spreadsheet->execute();
    _doc->recompute();

    //
//    App::ObjectIdentifier p(ObjectIdentifier::parse(getDocumentObjectPtr(), path));
//    const char * exprStr = PyUnicode_AsUTF8(expr);
//    std::shared_ptr<Expression> shared_expr(Expression::parse(getDocumentObjectPtr(), exprStr));
//    if (shared_expr && comment)
//            shared_expr->comment = comment;
//
//    getDocumentObjectPtr()->setExpression(p, shared_expr);

    auto boxLength = App::ObjectIdentifier::parse(box, "Length");
    std::shared_ptr<App::Expression> expression(App::Expression::parse(box, "Spreadsheet.A1"));

    // >>> Set Expression A1 to Box length
    // App.getDocument('Unnamed').Box.setExpression('Length', u'Spreadsheet.A1')

    // Act
    box->setExpression(boxLength, expression);

    int xxxx = 4;

    // Assert
}
