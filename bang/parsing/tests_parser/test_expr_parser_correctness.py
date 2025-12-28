import random
import string

import pytest

from bang.lexing.lexer import Lexer, LexerError, TokenType


def lex_string(source_code: str, tmp_path):
    p = tmp_path / "temp.bang"
    p.write_text(source_code, encoding="utf-8")
    return Lexer(str(p)).tokenizer()


def types(tokens):
    return [t.type for t in tokens]


def assert_tok(tok, ttype, value=None, line=None, col_start=None, col_end=None):
    assert tok.type == ttype
    if value is not None:
        assert tok.value == value
    if line is not None:
        assert tok.line == line
    if col_start is not None:
        assert tok.column_start == col_start
    if col_end is not None:
        assert tok.column_end == col_end


# ----------------------------
# Basic: EOF & whitespace
# ----------------------------

def test_always_ends_with_eof(tmp_path):
    toks = lex_string("", tmp_path)
    assert len(toks) == 1
    assert_tok(toks[0], TokenType.T_EOF, value="")


def test_ignores_whitespace(tmp_path):
    toks = lex_string("   \n\t 42 \n\n   ", tmp_path)
    assert types(toks) == [TokenType.T_INT, TokenType.T_EOF]
    assert toks[0].value == 42


# ----------------------------
# Numbers
# ----------------------------

@pytest.mark.parametrize(
    "src, expected",
    [
        ("0", 0),
        ("7", 7),
        ("42", 42),
        ("00012", 12),
        ("1234567890", 1234567890),
    ],
)
def test_integer_token_values(tmp_path, src, expected):
    toks = lex_string(src, tmp_path)
    assert types(toks) == [TokenType.T_INT, TokenType.T_EOF]
    assert toks[0].value == expected


@pytest.mark.parametrize(
    "src, expected",
    [
        ("3.14", 3.14),
        (".5", 0.5),
        ("2.", 2.0),
        ("0.0", 0.0),
        ("10.000", 10.0),
    ],
)
def test_float_token_values(tmp_path, src, expected):
    toks = lex_string(src, tmp_path)
    assert types(toks) == [TokenType.T_FLOAT, TokenType.T_EOF]
    assert toks[0].value == pytest.approx(expected)


@pytest.mark.parametrize("src", ["1.2.3", "0..1", ".1."])
def test_multiple_decimal_error(tmp_path, src):
    with pytest.raises(LexerError):
        lex_string(src, tmp_path)


# ----------------------------
# Identifiers / keywords / literals
# ----------------------------

@pytest.mark.parametrize(
    "src, expected_type, expected_value",
    [
        ("abc", TokenType.T_IDENT, "abc"),
        ("a1", TokenType.T_IDENT, "a1"),
        ("_x", TokenType.T_IDENT, "_x"),
        ("_", TokenType.T_IDENT, "_"),
        ("true", TokenType.T_TRUE, "true"),
        ("false", TokenType.T_FALSE, "false"),
        ("none", TokenType.T_NONE, "none"),
        ("if", TokenType.T_IF, "if"),
        ("elif", TokenType.T_ELIF, "elif"),
        ("else", TokenType.T_ELSE, "else"),
        ("for", TokenType.T_FOR, "for"),
        ("while", TokenType.T_WHILE, "while"),
        ("break", TokenType.T_BREAK, "break"),
        ("continue", TokenType.T_CONTINUE, "continue"),
        ("return", TokenType.T_RETURN, "return"),
        ("end", TokenType.T_END, "end"),
        ("fn", TokenType.T_FN, "fn"),
        ("data", TokenType.T_DATA, "data"),
        # Operator keyword
        ("in", TokenType.T_IN, "in"),
        # Keyword prefix should remain identifier
        ("endif", TokenType.T_IDENT, "endif"),
        ("inline", TokenType.T_IDENT, "inline"),
        ("forx", TokenType.T_IDENT, "forx"),
        ("truee", TokenType.T_IDENT, "truee"),
    ],
)
def test_identifier_keywords_and_literals(tmp_path, src, expected_type, expected_value):
    toks = lex_string(src, tmp_path)
    assert types(toks) == [expected_type, TokenType.T_EOF]
    assert toks[0].value == expected_value


# ----------------------------
# Strings
# ----------------------------

def test_string_token_basic(tmp_path):
    toks = lex_string('"hello"', tmp_path)
    assert types(toks) == [TokenType.T_STR, TokenType.T_EOF]
    assert toks[0].value == "hello"


def test_string_can_contain_hash_without_comment(tmp_path):
    toks = lex_string('"# not a comment"', tmp_path)
    assert types(toks) == [TokenType.T_STR, TokenType.T_EOF]
    assert toks[0].value == "# not a comment"


def test_unterminated_string_error(tmp_path):
    with pytest.raises(LexerError):
        lex_string('"hello', tmp_path)


# ----------------------------
# Operators & punctuation
# ----------------------------

@pytest.mark.parametrize(
    "src, expected_types",
    [
        ("+", [TokenType.T_PLUS]),
        ("-", [TokenType.T_MINUS]),
        ("*", [TokenType.T_STAR]),
        ("/", [TokenType.T_FSLASH]),
        ("//", [TokenType.T_DSLASH]),
        ("**", [TokenType.T_DOUBLESTAR]),
        ("=", [TokenType.T_EQ]),
        ("==", [TokenType.T_DOUBLEEQ]),
        ("!=", [TokenType.T_NOTEQUAL]),
        (">", [TokenType.T_GT]),
        ("<", [TokenType.T_LT]),
        (">=", [TokenType.T_GTE]),
        ("<=", [TokenType.T_LTE]),
        ("&&", [TokenType.T_AND]),
        ("||", [TokenType.T_OR]),
        ("!", [TokenType.T_BANG]),
        ("(", [TokenType.T_LPAREN]),
        (")", [TokenType.T_RPAREN]),
        ("[", [TokenType.T_LBRACKET]),
        ("]", [TokenType.T_RBRACKET]),
        ("{", [TokenType.T_LBRACE]),
        ("}", [TokenType.T_RBRACE]),
        (",", [TokenType.T_COMMA]),
        (".", [TokenType.T_DOT]),
        (";", [TokenType.T_SEMI]),
        ("+=", [TokenType.T_PLUS_ASSIGN]),
        ("-=", [TokenType.T_MINUS_ASSIGN]),
        ("*=", [TokenType.T_STAR_ASSIGN]),
        ("/=", [TokenType.T_FSLASH_ASSIGN]),
    ],
)
def test_operators_and_punctuation(tmp_path, src, expected_types):
    toks = lex_string(src, tmp_path)
    assert types(toks) == expected_types + [TokenType.T_EOF]


def test_operator_longest_match_examples(tmp_path):
    # "===" -> "==" then "="
    toks = lex_string("===", tmp_path)
    assert types(toks) == [TokenType.T_DOUBLEEQ, TokenType.T_EQ, TokenType.T_EOF]

    # "****" -> "**" then "**"
    toks = lex_string("****", tmp_path)
    assert types(toks) == [TokenType.T_DOUBLESTAR, TokenType.T_DOUBLESTAR, TokenType.T_EOF]


# ----------------------------
# Comments
# ----------------------------

def test_comment_only_line(tmp_path):
    toks = lex_string("# hello\n42", tmp_path)
    assert types(toks) == [TokenType.T_INT, TokenType.T_EOF]
    assert toks[0].value == 42
    assert toks[0].line == 2


def test_comment_after_code(tmp_path):
    toks = lex_string("x = 1 # comment here\ny = 2", tmp_path)
    assert types(toks) == [
        TokenType.T_IDENT, TokenType.T_EQ, TokenType.T_INT,
        TokenType.T_IDENT, TokenType.T_EQ, TokenType.T_INT,
        TokenType.T_EOF,
    ]
    assert toks[0].value == "x"
    assert toks[2].value == 1
    assert toks[3].value == "y"
    assert toks[5].value == 2


# ----------------------------
# Line/column metadata sanity checks
# ----------------------------

def test_metadata_single_line_positions(tmp_path):
    # 12345
    # x = 42
    toks = lex_string("x = 42", tmp_path)
    assert_tok(toks[0], TokenType.T_IDENT, value="x", line=1, col_start=1, col_end=1)
    assert_tok(toks[1], TokenType.T_EQ, value="=", line=1, col_start=3, col_end=3)
    assert_tok(toks[2], TokenType.T_INT, value=42, line=1, col_start=5, col_end=6)


def test_metadata_multi_line_positions(tmp_path):
    src = "x=1\ny = 2\n  z=3"
    toks = lex_string(src, tmp_path)
    # x=1
    assert_tok(toks[0], TokenType.T_IDENT, "x", line=1, col_start=1, col_end=1)
    assert_tok(toks[1], TokenType.T_EQ, "=", line=1, col_start=2, col_end=2)
    assert_tok(toks[2], TokenType.T_INT, 1, line=1, col_start=3, col_end=3)
    # y = 2
    assert_tok(toks[3], TokenType.T_IDENT, "y", line=2, col_start=1, col_end=1)
    assert_tok(toks[4], TokenType.T_EQ, "=", line=2, col_start=3, col_end=3)
    assert_tok(toks[5], TokenType.T_INT, 2, line=2, col_start=5, col_end=5)
    # "  z=3"
    assert_tok(toks[6], TokenType.T_IDENT, "z", line=3, col_start=3, col_end=3)
    assert_tok(toks[7], TokenType.T_EQ, "=", line=3, col_start=4, col_end=4)
    assert_tok(toks[8], TokenType.T_INT, 3, line=3, col_start=5, col_end=5)


def test_string_metadata_includes_quotes_in_span(tmp_path):
    toks = lex_string('"ab"', tmp_path)
    # string token spans columns 1..4 (includes both quotes)
    assert_tok(toks[0], TokenType.T_STR, "ab", line=1, col_start=1, col_end=4)


# ----------------------------
# Invalid characters & error location sanity
# ----------------------------

def test_invalid_character_raises(tmp_path):
    with pytest.raises(LexerError):
        lex_string("@", tmp_path)


def test_invalid_character_in_middle(tmp_path):
    with pytest.raises(LexerError):
        lex_string("x = 1 @ y", tmp_path)


# ----------------------------
# Mixed programs / integration-ish lexer checks
# ----------------------------

def test_simple_expression_stream(tmp_path):
    toks = lex_string("a+=1; b = a**2 // 3", tmp_path)
    assert types(toks) == [
        TokenType.T_IDENT, TokenType.T_PLUS_ASSIGN, TokenType.T_INT, TokenType.T_SEMI,
        TokenType.T_IDENT, TokenType.T_EQ, TokenType.T_IDENT, TokenType.T_DOUBLESTAR,
        TokenType.T_INT, TokenType.T_DSLASH, TokenType.T_INT,
        TokenType.T_EOF,
    ]


def test_in_operator_in_context(tmp_path):
    toks = lex_string("0 in [1,2,3]", tmp_path)
    assert types(toks) == [
        TokenType.T_INT, TokenType.T_IN, TokenType.T_LBRACKET,
        TokenType.T_INT, TokenType.T_COMMA, TokenType.T_INT, TokenType.T_COMMA, TokenType.T_INT,
        TokenType.T_RBRACKET,
        TokenType.T_EOF,
    ]


# ----------------------------
# Deterministic fuzz-like coverage
# ----------------------------

def test_many_valid_random_streams(tmp_path):
    # We intentionally generate only "safe" pieces that should always lex.
    rng = random.Random(1337)

    keywords = [
        "if", "elif", "else", "for", "while", "break", "continue", "return", "end", "fn", "data",
        "true", "false", "none", "in",
    ]
    # Keep operators here to those you support (and that are unambiguous in lexer)
    ops = [
        "+", "-", "*", "/", "//", "**", "=", "==", "!=", ">", "<", ">=", "<=", "&&", "||", "!", ",", ".", ";",
        "(", ")", "[", "]", "{", "}",
        "+=", "-=", "*=", "/=",
    ]

    def rand_ident():
        first = rng.choice(string.ascii_letters + "_")
        rest = "".join(rng.choice(string.ascii_letters + string.digits + "_") for _ in range(rng.randint(0, 10)))
        s = first + rest
        # avoid producing exact keywords too often unless chosen explicitly
        if s in keywords:
            s = s + "_x"
        return s

    def rand_number():
        if rng.random() < 0.7:
            return str(rng.randint(0, 10_000))
        # float forms (avoid multiple dots)
        if rng.random() < 0.5:
            return f"{rng.randint(0, 999)}.{rng.randint(0, 999)}"
        return f".{rng.randint(0, 999)}"

    def expected_type(piece: str):
        if piece == "true":
            return TokenType.T_TRUE
        if piece == "false":
            return TokenType.T_FALSE
        if piece == "none":
            return TokenType.T_NONE
        if piece in ("if", "elif", "else", "for", "while", "break", "continue", "return", "end", "fn", "data"):
            return getattr(TokenType, f"T_{piece.upper()}")
        if piece == "in":
            return TokenType.T_IN
        if piece in ops:
            # map operator lexeme to TokenType by explicit dict
            op_map = {
                "+": TokenType.T_PLUS,
                "-": TokenType.T_MINUS,
                "*": TokenType.T_STAR,
                "/": TokenType.T_FSLASH,
                "//": TokenType.T_DSLASH,
                "**": TokenType.T_DOUBLESTAR,
                "=": TokenType.T_EQ,
                "==": TokenType.T_DOUBLEEQ,
                "!=": TokenType.T_NOTEQUAL,
                ">": TokenType.T_GT,
                "<": TokenType.T_LT,
                ">=": TokenType.T_GTE,
                "<=": TokenType.T_LTE,
                "&&": TokenType.T_AND,
                "||": TokenType.T_OR,
                "!": TokenType.T_BANG,
                "(": TokenType.T_LPAREN,
                ")": TokenType.T_RPAREN,
                "[": TokenType.T_LBRACKET,
                "]": TokenType.T_RBRACKET,
                "{": TokenType.T_LBRACE,
                "}": TokenType.T_RBRACE,
                ",": TokenType.T_COMMA,
                ".": TokenType.T_DOT,
                ";": TokenType.T_SEMI,
                "+=": TokenType.T_PLUS_ASSIGN,
                "-=": TokenType.T_MINUS_ASSIGN,
                "*=": TokenType.T_STAR_ASSIGN,
                "/=": TokenType.T_FSLASH_ASSIGN,
            }
            return op_map[piece]
        # numbers
        if piece.startswith(".") or "." in piece:
            return TokenType.T_FLOAT
        if piece.isdigit():
            return TokenType.T_INT
        return TokenType.T_IDENT

    for _ in range(150):
        pieces = []
        for _ in range(rng.randint(5, 60)):
            r = rng.random()
            if r < 0.25:
                pieces.append(rng.choice(keywords))
            elif r < 0.55:
                pieces.append(rng.choice(ops))
            elif r < 0.75:
                pieces.append(rand_number())
            else:
                pieces.append(rand_ident())

        src = " ".join(pieces)
        toks = lex_string(src, tmp_path)

        expected = [expected_type(p) for p in pieces] + [TokenType.T_EOF]
        got = types(toks)
        assert got == expected, f"\nSRC:\n{src}\n\nEXPECTED:\n{expected}\n\nGOT:\n{got}\n"
