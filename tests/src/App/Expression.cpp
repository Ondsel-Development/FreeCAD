#include "gtest/gtest.h"

#include <tuple>

#include "App/ExpressionParser.h"
#include "App/ExpressionTokenizer.h"

// clang-format off
TEST(Expression, tokenize)
{
    EXPECT_EQ(App::ExpressionTokenizer().perform(QString::fromUtf8(""), 10), QString());
    // 0.0000 deg-
    EXPECT_EQ(App::ExpressionTokenizer().perform(QString::fromUtf8("0.00000 \xC2\xB0-"), 10), QString());
    EXPECT_EQ(App::ExpressionTokenizer().perform(QString::fromUtf8("0.00000 \xC2\xB0-s"), 11), QString::fromLatin1("s"));
    EXPECT_EQ(App::ExpressionTokenizer().perform(QString::fromUtf8("0.00000 \xC2\xB0-ss"), 12), QString::fromLatin1("ss"));
    EXPECT_EQ(App::ExpressionTokenizer().perform(QString::fromUtf8("0.00000 deg"), 5), QString());
    EXPECT_EQ(App::ExpressionTokenizer().perform(QString::fromUtf8("0.00000 deg"), 11), QString::fromLatin1("deg"));
}

TEST(Expression, tokenizePi)
{
    EXPECT_EQ(App::ExpressionTokenizer().perform(QString::fromLatin1("p"), 1), QString::fromLatin1("p"));
    EXPECT_EQ(App::ExpressionTokenizer().perform(QString::fromLatin1("pi"), 2), QString());
    EXPECT_EQ(App::ExpressionTokenizer().perform(QString::fromLatin1("pi "), 3), QString());
    EXPECT_EQ(App::ExpressionTokenizer().perform(QString::fromLatin1("pi r"), 4), QString::fromLatin1("r"));
    EXPECT_EQ(App::ExpressionTokenizer().perform(QString::fromLatin1("pi ra"), 5), QString::fromLatin1("ra"));
    EXPECT_EQ(App::ExpressionTokenizer().perform(QString::fromLatin1("pi rad"), 6), QString::fromLatin1("rad"));
    EXPECT_EQ(App::ExpressionTokenizer().perform(QString::fromLatin1("pi rad"), 2), QString());
}

TEST(Expression, tokenizeDocumentProperty)
{
    // Arrange
    std::vector<std::tuple<int, int, std::string>> expectedTokens{
        { App::ExpressionParser::IDENTIFIER, 0, "myDocName" },
        { 36, 9, "$" }, // the "46" *might* be dynamic ?
        { App::ExpressionParser::IDENTIFIER, 10, "myProp" }
    };
    std::basic_string<char> srcString("myDocName$myProp");

    // Act
    std::vector<std::tuple<int, int, std::string>> result =
        App::ExpressionParser::tokenize(srcString);

    // Assert
    EXPECT_EQ(result.size(), expectedTokens.size());
    EXPECT_EQ(result[0], expectedTokens[0]);
    EXPECT_EQ(result[1], expectedTokens[1]);
    EXPECT_EQ(result[2], expectedTokens[2]);
}

TEST(Expression, tokenizeCurrentDocumentProperty)
{
    // Arrange
    std::vector<std::tuple<int, int, std::string>> expectedTokens{
        { 35, 0, "#" },
        { App::ExpressionParser::IDENTIFIER, 1, "myProp" }
    };
    std::basic_string<char> srcString("#myProp");

    // Act
    std::vector<std::tuple<int, int, std::string>> result =
        App::ExpressionParser::tokenize(srcString);

    // Assert
    EXPECT_EQ(result.size(), expectedTokens.size());
    EXPECT_EQ(result[0], expectedTokens[0]);
    EXPECT_EQ(result[1], expectedTokens[1]);
}

TEST(Expression, toString)
{
    App::UnitExpression expr{nullptr, Base::Quantity{}, "pi rad"};
    EXPECT_EQ(expr.toString(), "pi rad");
}

TEST(Expression, test_pi_rad)
{
    auto constant = std::make_unique<App::ConstantExpression>(nullptr, "pi");
    auto unit = std::make_unique<App::UnitExpression>(nullptr, Base::Quantity{}, "rad");
    auto op = std::make_unique<App::OperatorExpression>(nullptr, constant.get(), App::OperatorExpression::UNIT, unit.get());
    EXPECT_EQ(op->toString(), "pi rad");
    op.release();
}

TEST(Expression, test_e_rad)
{
    auto constant = std::make_unique<App::ConstantExpression>(nullptr, "e");
    auto unit = std::make_unique<App::UnitExpression>(nullptr, Base::Quantity{}, "rad");
    auto op = std::make_unique<App::OperatorExpression>(nullptr, constant.get(), App::OperatorExpression::UNIT, unit.get());
    EXPECT_EQ(op->toString(), "e rad");
    op.release();
}
// clang-format on
