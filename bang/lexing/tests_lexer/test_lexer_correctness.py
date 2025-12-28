import random
from pathlib import Path

import pytest

from bang.lexing.lexer import Lexer, LexerError

# Prefer TokenType from lexer_tokens, but fall back if you re-export elsewhere.
try:
    from bang.lexing.lexer_tokens import TokenType
except Exception:  # pragma: no cover
    from bang.lexing.lexer import TokenType  # type: ignore


# ----------------------------
# Helpers
# ----------------------------

def lex_string(src: str, tmp_path) -> list:
    p = Path(tmp_path) / "temp.bang"
    p.write_text(src, encoding="utf-8")
    return Lexer(str(p)).tokenizer()


def tok_type_enum_id(tok) -> int:
    """
    Supports:
      - new tokens: tok.type_enum_id (int)
      - legacy tokens: tok.type (TokenType or int)
    """
    if hasattr(tok, "type_enum_id"):
        return int(tok.type_enum_id)
    if hasattr(tok, "type"):
        t = tok.type
        return int(t.value) if hasattr(t, "value") else int(t)
    raise AssertionError(f"Token has no type_enum_id/type: {tok!r}")


def tok_type(tok) -> TokenType:
    return TokenType(tok_type_enum_id(tok))


def tok_value(tok) -> str:
    return getattr(tok, "value")


def err_text(err: Exception) -> str:
    # Your LexerError uses `.msg` :contentReference[oaicite:4]{index=4}
    if hasattr(err, "msg"):
        return str(getattr(err, "msg"))
    if hasattr(err, "message"):
        return str(getattr(err, "message"))
    return str(err)


def assert_types(tokens, expected_types):
    got = [tok_type(t) for t in tokens]
    assert got == expected_types, f"\nexpected: {expected_types}\n     got: {got}\nvalues: {[tok_value(t) for t in tokens]}"


def assert_lex_error(src: str, tmp_path, contains: str = None, line=None, col=None):
    with pytest.raises(LexerError) as e:
        lex_string(src, tmp_path)
    err = e.value

    if contains is not None:
        msg = err_text(err)
        assert contains in msg or contains in str(err), (
            f"expected error to contain {contains!r}\n"
            f"err_text={msg!r}\n"
            f"str(err)={str(err)!r}"
        )

    # Your LexerError exposes line_num/col :contentReference[oaicite:5]{index=5}
    if line is not None and hasattr(err, "line_num"):
        assert err.line_num == line
    if col is not None and hasattr(err, "col"):
        assert err.col == col


# ----------------------------
# Core behavior
# ----------------------------

def test_empty_input_returns_no_tokens(tmp_path):
    tokens = lex_string("", tmp_path)
    assert tokens == []


def test_whitespace_only_returns_no_tokens(tmp_path):
    tokens = lex_string("   \n\t\r  \n\n", tmp_path)
    assert tokens == []


def test_no_eof_token_is_emitted(tmp_path):
    tokens = lex_string("x=1\n", tmp_path)
    # Make sure no token value looks like the sentinel or EOF-ish marker.
    # (Your lexer stops at sentinel and returns existing tokens.) :contentReference[oaicite:6]{index=6}
    assert all(tok_value(t) != "\0" for t in tokens)


# ----------------------------
# Numbers / dot rules
# ----------------------------

@pytest.mark.parametrize(
    "src, expected_type, expected_val",
    [
        ("0", TokenType.T_INT, "0"),
        ("42", TokenType.T_INT, "42"),
        ("999", TokenType.T_INT, "999"),
        ("3.14", TokenType.T_FLOAT, "3.14"),
        (".5", TokenType.T_FLOAT, ".5"),
        ("5.", TokenType.T_FLOAT, "5."),
        (".", TokenType.T_DOT, "."),
    ],
)
def test_numbers_and_dot(tmp_path, src, expected_type, expected_val):
    tokens = lex_string(src, tmp_path)
    assert len(tokens) == 1
    assert tok_type(tokens[0]) == expected_type
    assert tok_value(tokens[0]) == expected_val


def test_too_many_decimals_error(tmp_path):
    assert_lex_error("1.2.3", tmp_path, contains="too many decimals")


def test_too_many_decimals_error_double_dot(tmp_path):
    assert_lex_error("1..2", tmp_path, contains="too many decimals")


# ----------------------------
# Identifiers / keywords / literals
# ----------------------------

@pytest.mark.parametrize("src", ["a", "abc", "hello_world123", "_tmp", "A1", "snake_case"])
def test_identifier_token(tmp_path, src):
    tokens = lex_string(src, tmp_path)
    assert len(tokens) == 1
    assert tok_type(tokens[0]) == TokenType.T_IDENT
    assert tok_value(tokens[0]) == src


def test_bool_literals(tmp_path):
    tokens = lex_string("true false", tmp_path)
    assert_types(tokens, [TokenType.T_BOOL, TokenType.T_BOOL])
    assert [tok_value(t) for t in tokens] == ["true", "false"]


def test_none_literal(tmp_path):
    tokens = lex_string("none", tmp_path)
    assert len(tokens) == 1
    assert tok_type(tokens[0]) == TokenType.T_NONE
    assert tok_value(tokens[0]) == "none"


def test_in_keyword_is_tokenized_as_in(tmp_path):
    tokens = lex_string("in", tmp_path)
    assert len(tokens) == 1
    assert tok_type(tokens[0]) == TokenType.T_IN
    assert tok_value(tokens[0]) == "in"


@pytest.mark.parametrize(
    "kw, ttype",
    [
        ("if", TokenType.T_IF),
        ("elif", TokenType.T_ELIF),
        ("else", TokenType.T_ELSE),
        ("for", TokenType.T_FOR),
        ("while", TokenType.T_WHILE),
        ("break", TokenType.T_BREAK),
        ("continue", TokenType.T_CONTINUE),
        ("return", TokenType.T_RETURN),
        ("end", TokenType.T_END),
        ("fn", TokenType.T_FN),
        ("data", TokenType.T_DATA),
    ],
)
def test_keywords(tmp_path, kw, ttype):
    tokens = lex_string(kw, tmp_path)
    assert len(tokens) == 1
    assert tok_type(tokens[0]) == ttype
    assert tok_value(tokens[0]) == kw


# ----------------------------
# Strings
# ----------------------------

def test_string_literal_value_strips_quotes(tmp_path):
    tokens = lex_string('"hello"', tmp_path)
    assert len(tokens) == 1
    assert tok_type(tokens[0]) == TokenType.T_STRING
    # Your lexer stores inner content only. :contentReference[oaicite:7]{index=7}
    assert tok_value(tokens[0]) == "hello"


def test_string_can_contain_spaces_and_symbols(tmp_path):
    tokens = lex_string('"a b c 123 #!?"', tmp_path)
    assert len(tokens) == 1
    assert tok_type(tokens[0]) == TokenType.T_STRING
    assert tok_value(tokens[0]) == 'a b c 123 #!?'


def test_unterminated_string_error(tmp_path):
    # Your lexer raises at the opening quote position. :contentReference[oaicite:8]{index=8}
    assert_lex_error('"hello', tmp_path, contains="unterminated string", line=1, col=1)


# ----------------------------
# Operators & punctuation (1-char and 2-char)
# ----------------------------

def test_single_char_symbols(tmp_path):
    code = "+ - * / = ! ( ) { } [ ] , ; ."
    tokens = lex_string(code, tmp_path)
    assert_types(
        tokens,
        [
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
            TokenType.T_SEMICOLON,
            TokenType.T_DOT,
        ],
    )


@pytest.mark.parametrize(
    "op, expected",
    [
        ("+=", TokenType.T_PLUS_ASSIGN),
        ("-=", TokenType.T_MINUS_ASSIGN),
        ("*=", TokenType.T_ASTERISK_ASSIGN),
        ("/=", TokenType.T_SLASH_ASSIGN),
        ("==", TokenType.T_EQ),
        ("!=", TokenType.T_NEQ),
        ("<=", TokenType.T_LEQ),
        (">=", TokenType.T_GTEQ),
        ("//", TokenType.T_DSLASH),
        ("**", TokenType.T_EXPO),
        ("&&", TokenType.T_AND),
        ("||", TokenType.T_OR),
    ],
)
def test_two_char_operators(tmp_path, op, expected):
    tokens = lex_string(op, tmp_path)
    assert len(tokens) == 1
    assert tok_type(tokens[0]) == expected
    assert tok_value(tokens[0]) == op


def test_mixed_operator_sequence_prefers_two_char(tmp_path):
    # Ensure it tokenizes as [==, !=, <=, >=, &&, ||] not broken apart.
    src = "a==b!=c<=d>=e&&f||g"
    tokens = lex_string(src, tmp_path)
    got = [tok_type(t) for t in tokens]
    assert got == [
        TokenType.T_IDENT,
        TokenType.T_EQ,
        TokenType.T_IDENT,
        TokenType.T_NEQ,
        TokenType.T_IDENT,
        TokenType.T_LEQ,
        TokenType.T_IDENT,
        TokenType.T_GTEQ,
        TokenType.T_IDENT,
        TokenType.T_AND,
        TokenType.T_IDENT,
        TokenType.T_OR,
        TokenType.T_IDENT,
    ]


# ----------------------------
# Comments
# ----------------------------

def test_comment_ignored_until_newline(tmp_path):
    src = "x=1 # comment here\ny=2\n"
    tokens = lex_string(src, tmp_path)
    assert_types(
        tokens,
        [TokenType.T_IDENT, TokenType.T_ASSIGN, TokenType.T_INT,
         TokenType.T_IDENT, TokenType.T_ASSIGN, TokenType.T_INT],
    )
    assert [tok_value(t) for t in tokens] == ["x", "=", "1", "y", "=", "2"]


def test_comment_at_eof_is_ok(tmp_path):
    src = "x=1 # trailing comment with no newline"
    tokens = lex_string(src, tmp_path)
    assert_types(tokens, [TokenType.T_IDENT, TokenType.T_ASSIGN, TokenType.T_INT])


# ----------------------------
# Positioning sanity checks
# ----------------------------

def test_error_position_invalid_char(tmp_path):
    # x=@\n => '@' should be line 1, col 3 with your col formula. :contentReference[oaicite:9]{index=9}
    assert_lex_error("x=@\n", tmp_path, contains="Token not recognized", line=1, col=3)


def test_token_columns_monotonic_on_line(tmp_path):
    tokens = lex_string("abc=12\n", tmp_path)
    # abc (col 1..?), =, 12 : just verify monotonicity and positive columns
    for t in tokens:
        assert t.column_start >= 1
        assert t.column_end >= t.column_start
    # strictly increasing starts
    starts = [t.column_start for t in tokens]
    assert starts == sorted(starts)


# ----------------------------
# Deterministic fuzz (valid-ish)
# ----------------------------

def _rand_valid_float(rng: random.Random) -> str:
    # at most one dot; avoid "." alone here
    style = rng.randint(0, 2)
    if style == 0:
        return f"{rng.randint(0, 999)}.{rng.randint(0, 999)}"
    if style == 1:
        return f".{rng.randint(0, 999)}"
    return f"{rng.randint(0, 999)}."


def test_randomized_smoke_validish_does_not_crash(tmp_path):
    """
    Generates *valid-ish* token soup (no unterminated strings, no multi-dot numbers).
    Goal: catch crashes/regressions in tight-loop lexer logic.
    """
    rng = random.Random(1337)

    kw_pool = [
        "if", "elif", "else", "for", "while", "break", "continue", "return", "end", "fn", "data",
        "true", "false", "none", "in",
    ]
    sym_pool = ["+", "-", "*", "/", "=", "!", "(", ")", "{", "}", "[", "]", ",", ";", ".", "<", ">", "<=", ">=",
                "==", "!=", "+=", "-=", "*=", "/=", "//", "**", "&&", "||"]
    ident_pool = ["x", "y", "foo", "bar", "_tmp", "A1", "snake_case"]
    int_pool = [str(i) for i in [0, 1, 2, 10, 999, 42]]

    def rand_string():
        # Always closed.
        inner = "".join(rng.choice("abc 123#") for _ in range(rng.randint(0, 12)))
        return f'"{inner}"'

    parts = []
    for _ in range(4000):
        choice = rng.randint(0, 6)
        if choice == 0:
            parts.append(rng.choice(kw_pool))
        elif choice == 1:
            parts.append(rng.choice(sym_pool))
        elif choice == 2:
            parts.append(rng.choice(ident_pool))
        elif choice == 3:
            parts.append(rng.choice(int_pool))
        elif choice == 4:
            parts.append(_rand_valid_float(rng))
        else:
            parts.append(rand_string())

        r = rng.random()
        if r < 0.12:
            parts.append(" ")
        elif r < 0.15:
            parts.append("\t")
        elif r < 0.18:
            parts.append("\n")
        elif r < 0.20:
            parts.append(" #comment\n")

    src = "".join(parts)

    # This should not raise anything other than LexerError (ideally not even that),
    # but we treat LexerError as acceptable in case the random soup creates a rare invalid adjacency.
    try:
        tokens = lex_string(src, tmp_path)
        assert isinstance(tokens, list)
        # basic sanity: all tokens have a valid TokenType
        for t in tokens:
            _ = tok_type(t)
    except LexerError as e:
        # still acceptable: must be a LexerError with formatted message and valid line/col
        assert "LexerError" in str(e)
        if hasattr(e, "line_num"):
            assert e.line_num >= 1
        if hasattr(e, "col"):
            assert e.col >= 1




