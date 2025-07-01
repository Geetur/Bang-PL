
# after this pass we are guaranteed to have a list
# of valid bang tokens

from lexer_tokens import (
    Lexeme,
    TokenType,
    NEWLINE,
    DECIMAL,
    SENTINEL,
    UNDERSCORE,
    STRING,
    COMMENT,
    SYMBOLS,
    KEYWORDS,
)



class LexerError(Exception):
    def __init__(self, file, msg, row, start, end):
        self.file = file
        self.msg = msg
        self.row = row
        self.start = start
        self.end = end

        super().__init__(self._format())
    
    def _format(self):
        error_line = self.file[self.row]
        print(error_line)
        crt_length = self.end - self.start if self.end - self.start != 0 else 1
        pointers = " " * self.start + "^" * crt_length
        return (
            f"[LexerError] Line {self.row + 1}, Column {self.start}-{self.end}:\n"
            f"{error_line.rstrip()}\n"
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

    def __init__(self, input_file):

        # could add an error here if file isn't guaranteed to exist
        with open(input_file, 'r') as f:
            self.file = f.readlines()

        self.start = 0
        self.row = 0
        self.col = 0
        self.prev_start= -1
        self.prev_row = -1
        self.prev_col = -1

        self.char = self.file[self.row][self.col] if self.file else SENTINEL

        self.token = ""
        self.tokens = []
        self.error_msg = ""
        
    def advance(self):
        
        self.prev_col = self.col; self.col += 1
        # if at a new row, reset col to zero and iterate row
        if self.row < len(self.file) and self.col >= len(self.file[self.row]):
            self.prev_row = self.row; self.row += 1
            self.col = 0
            self.start = 0
        # if at EOF mark char with sentinel
        if self.row >= len(self.file):
            self.char = SENTINEL
        # otherwise mark char with next arbitrary next character             
        else:
            self.char = self.file[self.row][self.col]
    
    def error_handler(self):
        # this function is half the reason for prev_start, prev_col, etc
        # because we need to advance at some points, but if the while loops
        # break after advancing and we reached end of row/file our self.col-1 logic
        # wouldn't work because col got reset to zero; so if its reset to zero, we use prev
        if self.col:
            raise LexerError(self.file, self.error_msg, self.row, self.start, self.col)
        else:
            raise LexerError(self.file, self.error_msg, self.prev_row, self.prev_start, self.prev_col)
    
    def flush_token(self, ttype, value):
        # same as above if we advance to a new row and reset to zero, we use prev
        end = None
        if self.col:
            end = self.col - 1 if self.col - 1 >= self.start else self.col
            self.tokens.append(Lexeme(ttype, value, self.row, self.start, end))
        else:
            end = self.prev_col - 1 if self.prev_col - 1 >= self.prev_start else self.prev_col
            self.tokens.append(Lexeme(ttype, value, self.prev_row, self.prev_start, end))
        
        # after flushing we want to forget the token and start a new one
        self.token = ""
        self.start = self.col

    def tokenizer(self):

        while self.char != SENTINEL:
            
            # a really interesting snippet of knowledge about programming lang
            # development is that comments are usually handled in the lexer
            # so, the idea is that anything after the comment until the newline
            # is just not tokenized; you could however store them in a seperate structure
            # so that if you transpile to another lang, the file still maintains comments however
            if self.char == COMMENT:
                while self.char not in (NEWLINE, SENTINEL):
                    self.advance()
                continue

            if self.char == STRING:
                self.prev_start = self.start; self.start = self.col
                value = ""
                self.advance()
                while self.char not in (NEWLINE, SENTINEL, STRING):
                    value += self.char
                    self.advance()
                if self.char != STRING:
                    self.error_msg = "unterminated string literal"
                    self.error_handler()
                self.flush_token(ttype=TokenType.T_STRING, value=value)
                self.advance()
                continue

            if self.char.isspace() or self.char == NEWLINE:
                self.advance()
                # have to reset start after every space, because say
                # we catch an error after 5 spaces, we want start to represent
                # the start of the error, not the end of the last token because
                # we error print from original text file
                self.prev_start = self.start; self.start = self.col
                continue
            
            elif self.char.isdigit() or self.char == DECIMAL:
                self.prev_start = self.start; self.start = self.col
                decimal_count = 0
                while self.char.isdigit() or self.char == DECIMAL:
                    if self.char == DECIMAL and decimal_count >= 1:
                        # we don't instantly break because we need to finish the token
                        # so when we error print we cant identify entire erroneous
                        # chunk of code
                        self.error_msg = "too many decimals in float (max 1)"
                    self.token += self.char
                    decimal_count += 1 if self.char == DECIMAL else 0
                    self.advance()
                if self.error_msg:
                    self.error_handler()
                ttype = TokenType.T_FLOAT if decimal_count else TokenType.T_INT
                self.flush_token(ttype, self.token)
                continue
            
            # our identifies can start with underscore or letter only
            # but can continue indefinitely with alnum and underscore
            elif self.char.isalpha() or self.char == UNDERSCORE:
                self.prev_start = self.start; self.start = self.col
                while self.char.isalnum() or self.char == UNDERSCORE:
                    self.token += self.char
                    self.advance()
                # these ifs can probably be replaced with a
                # literal-to-word map is they keep growing
                if self.token in ("true", "false"):
                    ttype = TokenType.T_BOOL
                elif self.token == "none":
                    ttype = TokenType.T_NONE
                elif self.token in KEYWORDS:
                    ttype = KEYWORDS[self.token]
                else:
                    ttype = TokenType.T_IDENT
                self.flush_token(ttype, self.token)
                continue
            
            if self.char in SYMBOLS or self.char not in SYMBOLS:
                self.prev_start = self.start; self.start = self.col
                operator = self.char
                self.advance()
                two = operator + self.char
                if two in SYMBOLS:
                    operator = two
                    # we're only advancing within the if statement
                    # so we don't potentially skip a token
                    self.advance()
                if len(operator) == 1 and operator not in SYMBOLS:
                    self.error_msg = "token not recognized"
                    self.error_handler()
                
                self.flush_token(SYMBOLS[operator], operator)
                continue
            # this only pops if the characters isn't in symbols, isn't a digit, and isn't
            # a letter; it must be a unrecognized symbol such as ^
        return self.tokens
    