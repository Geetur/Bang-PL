import pytest

from bang.lexing.lexer import Lexer, LexerError, TokenType


def lex_string(source_code: str):
    with open("temp.txt", "w") as f:
        f.write(source_code)
    return Lexer("temp.txt").tokenizer()


# Numbers
def test_integer_token():
    tokens = lex_string("42")
    assert tokens[0].type == TokenType.T_INT
    assert tokens[0].value == "42"


def test_float_token():
    tokens = lex_string("3.14")
    assert tokens[0].type == TokenType.T_FLOAT
    assert tokens[0].value == "3.14"


def test_float_with_leading_dot():
    tokens = lex_string(".5")
    assert tokens[0].type == TokenType.T_FLOAT
    assert tokens[0].value == ".5"


def test_float_with_trailing_dot():
    tokens = lex_string("2.")
    assert tokens[0].type == TokenType.T_FLOAT
    assert tokens[0].value == "2."


# Identifiers and Keywords
def test_identifier_token():
    tokens = lex_string("hello_world123")
    assert tokens[0].type == TokenType.T_IDENT
    assert tokens[0].value == "hello_world123"


def test_keywords():
    for kw, tok_type in Lexer.KEYWORDS.items():
        tokens = lex_string(kw)
        assert tokens[0].type == tok_type


# Operators & Symbols
def test_single_char_operators():
    code = "+ - * / = ! ( ) { } [ ] ,"
    expected = [
        TokenType.T_PLUS,
        TokenType.T_MINUS,
        TokenType.T_ASTERISK,
        TokenType.T_SLASH,
        TokenType.T_ASSIGN,
        TokenType.T_NEGATE,
        TokenType.T_LPAREN,
        TokenType.T_RPAREN,
        TokenType.T_LBRACE,
        TokenType.T_RBRACE,
        TokenType.T_LBRACKET,
        TokenType.T_RBRACKET,
        TokenType.T_COMMA,
    ]
    tokens = lex_string(code)
    assert [t.type for t in tokens] == expected


# Logical Combinations
def test_multi_char_operators():
    ops = {
        "+=": TokenType.T_PLUS_ASSIGN,
        "-=": TokenType.T_MINUS_ASSIGN,
        "*=": TokenType.T_ASTERISK_ASSIGN,
        "/=": TokenType.T_SLASH_ASSIGN,
        "==": TokenType.T_EQ,
        "!=": TokenType.T_NEQ,
        "<": TokenType.T_LT,
        "<=": TokenType.T_LEQ,
        ">": TokenType.T_GT,
        ">=": TokenType.T_GTEQ,
        "//": TokenType.T_DSLASH,
        "**": TokenType.T_EXPO,
        "&&": TokenType.T_AND,
        "||": TokenType.T_OR,
    }
    for op, expected_type in ops.items():
        tokens = lex_string(op)
        assert len(tokens) == 1
        assert tokens[0].type == expected_type


# Error Handling Tests


def test_multiple_decimal_error():
    with pytest.raises(LexerError) as exc:
        lex_string("1.2.3")
    assert "too many decimals" in str(exc.value)


def test_invalid_character():
    with pytest.raises(LexerError) as exc:
        lex_string("@")
    assert "token not recognized" in str(exc.value)


# Boolean Literals


def test_boolean_literals():
    tokens = lex_string("true false")
    assert tokens[0].type == TokenType.T_BOOL
    assert tokens[0].value == "true"
    assert tokens[1].type == TokenType.T_BOOL
    assert tokens[1].value == "false"


# Whitespace Handling
def test_ignores_whitespace():
    tokens = lex_string("   \n\t 42 \n\n   ")
    assert len(tokens) == 1
    assert tokens[0].type == TokenType.T_INT
