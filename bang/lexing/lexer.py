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
    UNDERSCORE,
    Lexeme,
    TokenType,
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
    # so, we want to make these things attributes of the lexer class
    # because they are important constants that our parser and other phases
    # would like to use without having to redefine, but  it is more modular, readable,
    # and clean to define them seperately
    NEWLINE = NEWLINE
    DECIMAL = DECIMAL
    SENTINEL = SENTINEL
    STRING = STRING
    UNDERSCORE = UNDERSCORE
    SYMBOLS = SYMBOLS
    KEYWORDS = KEYWORDS

    def __init__(self, file_path):
        # reading entire file to memory
        with open(file_path) as f:
            self.text = f.read() + SENTINEL

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
        T_INT = TokenType.T_INT
        T_FLOAT = TokenType.T_FLOAT
        T_DOT = TokenType.T_DOT
        T_STRING = TokenType.T_STRING
        T_IDENT = TokenType.T_IDENT
        T_BOOL = TokenType.T_BOOL
        T_NONE = TokenType.T_NONE
        T_IN = TokenType.T_IN

        # cache dictionaries
        kw_map = KEYWORDS
        sym_map = SYMBOLS

        def create_lexeme(ttype, val, start_pos, end_pos):
            # + 1 because zero index
            col_start = start_pos - line_start + 1
            col_end = end_pos - line_start + 1
            return Lexeme(ttype, ttype.value, val, line, col_start, col_end)

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
                    tokens.append(create_lexeme(T_BOOL, value, start, pos))
                elif value == "none":
                    tokens.append(create_lexeme(T_NONE, value, start, pos))
                elif value == "in":
                    tokens.append(create_lexeme(T_IN, value, start, pos))
                elif value in kw_map:
                    tokens.append(create_lexeme(kw_map[value], value, start, pos))
                else:
                    tokens.append(create_lexeme(T_IDENT, value, start, pos))

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
                        tokens.append(create_lexeme(T_DOT, value, start, pos))
                    else:
                        tokens.append(create_lexeme(T_FLOAT, value, start, pos))
                else:
                    tokens.append(create_lexeme(T_INT, value, start, pos))
                continue

            if char == STRING:
                start = pos
                # Find the closing quote instantly using C-implementation
                end_quote = text.find(STRING, pos + 1)

                if end_quote == -1:
                    raise LexerError("unterminated string literal", text, pos)

                value = text[pos + 1 : end_quote]  # Extract content without quotes
                pos = end_quote + 1
                tokens.append(create_lexeme(T_STRING, value, start, pos))
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
                if two_char in sym_map:
                    tokens.append(create_lexeme(sym_map[two_char], two_char, pos, pos + 2))
                    pos += 2
                    continue

            # Try 1-char symbol
            if char in sym_map:
                tokens.append(create_lexeme(sym_map[char], char, pos, pos + 1))
                pos += 1
                continue

            # if everything else fails, it must be an unrecognized symbol

            raise LexerError("Token not recognized", text, pos)
        return self.tokens
