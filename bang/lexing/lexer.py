# after this pass we are guaranteed to have a list
# of valid bang tokens

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
    T_IDENT_ENUM_VAL,
    T_IN_ENUM_VAL,
    T_INT_ENUM_VAL,
    T_NONE_ENUM_VAL,
    T_STRING_ENUM_VAL,
    UNDERSCORE,
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
        pointers = " " * (self.col - 1) + "^"
        return (
            f"[LexerError] Line {self.line_num}, Column {self.col}:\n"
            f"{self.line_text}\n"
            f"{pointers}\n"
            f"{self.msg}"
        )

    def __str__(self) -> str:
        return self._format()

    __repr__ = __str__


class Lexer:
    T_INT_ENUM_VAL = T_INT_ENUM_VAL
    T_FLOAT_ENUM_VAL = T_FLOAT_ENUM_VAL
    T_DOT_ENUM_VAL = T_DOT_ENUM_VAL
    T_STRING_ENUM_VAL = T_STRING_ENUM_VAL
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
        with open(file_path) as f:
            self.text = f.read() + self.SENTINEL

        # result of lexing will be list of tokens
        self.tokens = []

    def tokenizer(self):
        tokens = self.tokens
        text = self.text
        len_text = len(text)
        pos = 0
        line = 1
        line_start = 0

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
                break

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

            if char.isdigit() or char == DECIMAL:
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
                    if not (char.isdigit() or char == DECIMAL):
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
                # Find the closing quote instantly using C-implementation
                end_quote = text.find(STRING, pos + 1)

                if end_quote == -1:
                    raise LexerError("unterminated string literal", text, pos)

                value = text[pos + 1 : end_quote]  # Extract content without quotes
                pos = end_quote + 1
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
        return self.tokens
