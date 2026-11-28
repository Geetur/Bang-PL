# after this pass we are guaranteed to have a list
# of valid bang tokens

from bang.diagnostics import render_error
from bang.lexing.lexer_tokens import (
    COMMENT,
    DECIMAL,
    KEYWORDS,
    NEWLINE,
    SENTINEL,
    STRING,
    SYMBOLS,
    T_BOOL_ENUM_VAL,
    T_DOT_ENUM_VAL,
    T_FLOAT_ENUM_VAL,
    T_FSTRING_ENUM_VAL,
    T_IDENT_ENUM_VAL,
    T_IN_ENUM_VAL,
    T_INT_ENUM_VAL,
    T_NONE_ENUM_VAL,
    T_STRING_ENUM_VAL,
    UNDERSCORE,
    InterpolationField,
    Lexeme,
)


class LexerError(Exception):
    def __init__(self, msg, text, pos):
        # We lazily calculate the line/col only when an error actually happens
        self.msg = msg
        self.text = text
        self.pos = pos
        self.line_num = text.count(NEWLINE, 0, pos) + 1
        last_newline = text.rfind(NEWLINE, 0, pos)
        self.col = pos - last_newline

        # Extract the line text for the error message
        start_line = last_newline + 1
        end_line = text.find(NEWLINE, pos)
        if end_line == -1:
            end_line = len(text)
        self.line_text = text[start_line:end_line]

        super().__init__(self._format())

    def _format(self):
        return render_error("LexerError", self.text, self.msg, self.line_num, self.col)

    def __str__(self) -> str:
        return self._format()

    __repr__ = __str__


class Lexer:
    MAX_STRING_DEPTH = 64

    T_INT_ENUM_VAL = T_INT_ENUM_VAL
    T_FLOAT_ENUM_VAL = T_FLOAT_ENUM_VAL
    T_DOT_ENUM_VAL = T_DOT_ENUM_VAL
    T_STRING_ENUM_VAL = T_STRING_ENUM_VAL
    T_FSTRING_ENUM_VAL = T_FSTRING_ENUM_VAL
    T_IDENT_ENUM_VAL = T_IDENT_ENUM_VAL
    T_BOOL_ENUM_VAL = T_BOOL_ENUM_VAL
    T_NONE_ENUM_VAL = T_NONE_ENUM_VAL
    T_IN_ENUM_VAL = T_IN_ENUM_VAL

    COMMENT = COMMENT
    DECIMAL = DECIMAL
    NEWLINE = NEWLINE
    SENTINEL = SENTINEL
    STRING = STRING
    UNDERSCORE = UNDERSCORE

    # cache dictionaries
    KEYWORDS = KEYWORDS
    SYMBOLS = SYMBOLS

    def __init__(self, file_path):
        # reading entire file to memory
        try:
            with open(file_path, encoding="utf-8") as f:
                source = f.read()
        except UnicodeError as error:
            raise LexerError("source must be valid UTF-8", "", 0) from error
        if "\0" in source:
            raise LexerError("NUL characters are not allowed in source", source, source.index("\0"))
        self.text = source + self.SENTINEL

        # result of lexing will be list of tokens
        self.tokens = []

    def tokenizer(self):
        self.tokens.extend(self._tokenize(0, len(self.text) - 1, line=1, line_start=0))
        return self.tokens

    @classmethod
    def tokenize_fragment(cls, text, field):
        lexer = cls.__new__(cls)
        lexer.text = text
        return lexer._tokenize(
            field.start, field.stop, line=field.line, line_start=field.line_start
        )

    def _tokenize(self, start, stop, *, line, line_start):
        tokens = []
        text = self.text
        len_text = stop
        pos = start

        # localizing token types to avoid lookups
        T_INT_ENUM_VAL = self.T_INT_ENUM_VAL
        T_FLOAT_ENUM_VAL = self.T_FLOAT_ENUM_VAL
        T_DOT_ENUM_VAL = self.T_DOT_ENUM_VAL
        T_STRING_ENUM_VAL = self.T_STRING_ENUM_VAL
        T_IDENT_ENUM_VAL = self.T_IDENT_ENUM_VAL
        T_BOOL_ENUM_VAL = self.T_BOOL_ENUM_VAL
        T_NONE_ENUM_VAL = self.T_NONE_ENUM_VAL
        T_IN_ENUM_VAL = self.T_IN_ENUM_VAL

        COMMENT = self.COMMENT
        DECIMAL = self.DECIMAL
        NEWLINE = self.NEWLINE
        SENTINEL = self.SENTINEL
        STRING = self.STRING
        UNDERSCORE = self.UNDERSCORE

        # cache dictionaries
        KEYWORDS = self.KEYWORDS
        SYMBOLS = self.SYMBOLS

        def create_lexeme(ttype_id, val, start_pos, end_pos):
            # + 1 because zero index
            col_start = start_pos - line_start + 1
            col_end = end_pos - line_start + 1
            return Lexeme(ttype_id, val, line, col_start, col_end)

        # conditions most likely to occur, or necessary ones,
        # are places at the top of while loop to avoid checking
        # unlikely conditions
        while pos < len_text:
            char = text[pos]

            if char == NEWLINE:
                pos += 1
                line += 1
                line_start = pos
                continue

            if char in " \t\r":
                pos += 1
                continue

            if char == SENTINEL:
                raise LexerError("NUL characters are not allowed in source", text, pos)

            if char == "f" and pos + 1 < stop and text[pos + 1] == STRING:
                start = pos
                value, pos = self._read_string(
                    pos, stop, formatted=True, line=line, line_start=line_start
                )
                tokens.append(create_lexeme(self.T_FSTRING_ENUM_VAL, value, start, pos))
                continue

            if char.isalpha() or char == UNDERSCORE:
                start = pos
                while True:
                    pos += 1
                    # Accessing text[pos] directly is safe due to SENTINEL
                    char = text[pos]
                    if not (char.isalnum() or char == UNDERSCORE):
                        break

                value = text[start:pos]

                # heuristically speaking most likely to be bool
                if value == "true" or value == "false":
                    tokens.append(create_lexeme(T_BOOL_ENUM_VAL, value, start, pos))
                elif value == "none":
                    tokens.append(create_lexeme(T_NONE_ENUM_VAL, value, start, pos))
                elif value == "in":
                    tokens.append(create_lexeme(T_IN_ENUM_VAL, value, start, pos))
                elif value in KEYWORDS:
                    tokens.append(create_lexeme(KEYWORDS[value], value, start, pos))
                else:
                    tokens.append(create_lexeme(T_IDENT_ENUM_VAL, value, start, pos))

                continue

            if ("0" <= char <= "9") or char == DECIMAL:
                start = pos
                dot_seen = False

                # Manual loop is faster than checking isdigit function repeatedly
                while True:
                    if char == DECIMAL:
                        if dot_seen:
                            raise LexerError("too many decimals in float", text, pos)
                        dot_seen = True

                    pos += 1
                    char = text[pos]
                    if not (("0" <= char <= "9") or char == DECIMAL):
                        break

                value = text[start:pos]

                if dot_seen:
                    if len(value) == 1 and value == ".":
                        tokens.append(create_lexeme(T_DOT_ENUM_VAL, value, start, pos))
                    else:
                        tokens.append(create_lexeme(T_FLOAT_ENUM_VAL, value, start, pos))
                else:
                    tokens.append(create_lexeme(T_INT_ENUM_VAL, value, start, pos))
                continue

            if char == STRING:
                start = pos
                value, pos = self._read_string(pos, stop, line=line, line_start=line_start)
                tokens.append(create_lexeme(T_STRING_ENUM_VAL, value, start, pos))
                continue

            if char == COMMENT:
                # Find next newline instantly
                next_nl = text.find(NEWLINE, pos + 1)
                pos = len_text if next_nl == -1 else next_nl
                continue

            # operator handling
            # try two char symbol
            if pos + 1 < len(text):
                two_char = text[pos : pos + 2]
                if two_char in SYMBOLS:
                    tokens.append(create_lexeme(SYMBOLS[two_char], two_char, pos, pos + 2))
                    pos += 2
                    continue

            # Try 1-char symbol
            if char in SYMBOLS:
                tokens.append(create_lexeme(SYMBOLS[char], char, pos, pos + 1))
                pos += 1
                continue

            # if everything else fails, it must be an unrecognized symbol

            raise LexerError("Token not recognized", text, pos)
        return tokens

    def _read_string(self, start, stop, *, line, line_start, formatted=False, depth=0):
        if depth >= self.MAX_STRING_DEPTH:
            raise LexerError("string nesting exceeds the limit", self.text, start)
        text = self.text
        pos = start + (2 if formatted else 1)
        literal = []
        parts = []
        escapes = {
            "n": "\n",
            "r": "\r",
            "t": "\t",
            "b": "\b",
            "f": "\f",
            "v": "\v",
            '"': '"',
            "'": "'",
            "\\": "\\",
        }
        while pos < stop:
            char = text[pos]
            if char in "\r\n":
                raise LexerError("newline in string literal", text, start)
            if char == self.SENTINEL:
                raise LexerError("NUL characters are not allowed in source", text, pos)
            if char == '"':
                if not formatted:
                    return "".join(literal), pos + 1
                if literal:
                    parts.append("".join(literal))
                return tuple(parts), pos + 1
            if char == "\\":
                if pos + 1 < stop and text[pos + 1] in escapes:
                    literal.append(escapes[text[pos + 1]])
                    pos += 2
                else:
                    if pos + 1 >= stop:
                        raise LexerError("unterminated string literal", text, start)
                    if text[pos + 1] in "\r\n":
                        raise LexerError("newline in string literal", text, start)
                    raise LexerError(
                        f"unknown escape sequence {text[pos:pos + 2]!r}; "
                        "use '\\\\' for a literal backslash", text, pos,
                    )
                continue
            if formatted and char == "{":
                if pos + 1 < stop and text[pos + 1] == "{":
                    literal.append("{")
                    pos += 2
                    continue
                if literal:
                    parts.append("".join(literal))
                    literal = []
                end = self._field_end(
                    pos + 1, stop, line=line, line_start=line_start, depth=depth
                )
                if not text[pos + 1 : end].strip():
                    raise LexerError("empty interpolation field", text, pos)
                parts.append(InterpolationField(pos + 1, end, line, line_start))
                pos = end + 1
                continue
            if formatted and char == "}":
                if pos + 1 < stop and text[pos + 1] == "}":
                    literal.append("}")
                    pos += 2
                    continue
                raise LexerError(
                    "single '}' in interpolated string; use '}}' for a literal brace", text, pos
                )
            literal.append(char)
            pos += 1
        raise LexerError("unterminated string literal", text, start)

    def _field_end(self, start, stop, *, line, line_start, depth):
        text = self.text
        pairs = {"(": ")", "[": "]", "{": "}"}
        enders = set(pairs.values())
        openings = []
        pos = start
        while pos < stop:
            char = text[pos]
            if char in "\r\n":
                raise LexerError("newline in string literal", text, start - 1)
            if char == "#":
                raise LexerError("comments are not allowed in interpolation fields", text, pos)
            if char == "\\":
                raise LexerError("backslash outside a string in interpolation field", text, pos)
            if char == self.SENTINEL:
                raise LexerError("NUL characters are not allowed in source", text, pos)
            if char == '"':
                _, pos = self._read_string(
                    pos, stop, line=line, line_start=line_start, depth=depth + 1
                )
                continue
            if char.isalpha() or char == self.UNDERSCORE:
                end = pos + 1
                while end < stop and (text[end].isalnum() or text[end] == self.UNDERSCORE):
                    end += 1
                if text[pos:end] == "f" and end < stop and text[end] == '"':
                    _, pos = self._read_string(
                        pos,
                        stop,
                        formatted=True,
                        line=line,
                        line_start=line_start,
                        depth=depth + 1,
                    )
                else:
                    pos = end
                continue
            if char in pairs:
                openings.append(char)
            elif char in enders:
                if not openings:
                    if char == "}":
                        return pos
                    raise LexerError("mismatched interpolation delimiter", text, pos)
                if pairs[openings[-1]] != char:
                    raise LexerError("mismatched interpolation delimiter", text, pos)
                openings.pop()
            pos += 1
        raise LexerError("unterminated interpolation field", text, start - 1)
