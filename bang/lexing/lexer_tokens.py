from enum import Enum, auto
from dataclasses import dataclass

class TokenType(Enum):
    # Single-character tokens
    T_PLUS = auto()         # +
    T_MINUS = auto()        # -
    T_ASTERISK = auto()     # *
    T_SLASH = auto()        # /
    T_ASSIGN = auto()       # =
    T_NEGATE = auto()       # !

    # these unary tokens will not be
    # created in the lexer, but will
    # we useful for elegantly remapping
    # expressions into their unambiguous
    # versions, with unary support
    T_UPLUS = auto()
    T_UMINUS = auto()

    # Grouping & Punctuation
    T_LPAREN = auto()       # (
    T_RPAREN = auto()       # )
    T_LBRACE = auto()       # {
    T_RBRACE = auto()       # }
    T_LBRACKET = auto()     # [
    T_RBRACKET = auto()     # ]
    T_COMMA = auto()        # ,

    # Double-character tokens
    T_PLUS_ASSIGN = auto()      # +=
    T_MINUS_ASSIGN = auto()     # -=
    T_ASTERISK_ASSIGN = auto()  # *=
    T_SLASH_ASSIGN = auto()     # /=
    
    T_EQ = auto()           # ==
    T_NEQ = auto()          # !=
    T_LT = auto()           # <
    T_LEQ = auto()          # <=
    T_GT = auto()           # >
    T_GTEQ = auto()         # >=
    T_DSLASH = auto()       # //
    T_EXPO = auto()         # **
    T_AND = auto()
    T_OR = auto()


    # Literals
    T_NONE = auto()
    T_INT = auto()
    T_FLOAT = auto()
    T_BOOL = auto()
    T_STRING = auto()
    T_IDENT = auto()

    # Keywords
    T_IF = auto()
    T_ELIF = auto()
    T_ELSE = auto()
    T_FOR = auto()
    T_WHILE = auto()
    T_BREAK = auto()
    T_CONTINUE = auto()
    T_RETURN = auto()
    T_END = auto()
    T_FN = auto()
    T_IN = auto()


@dataclass 
class Lexeme:
    # dataclass for representing a single token of input after lexical analysis
    type: TokenType
    value: str
    line: int
    column_start: int
    column_end: int

    def __repr__(self):
        return f"Lexeme({self.type}, {self.value}, {self.line}, {self.column_start}, {self.column_end})"


# these constants aren't tokens but relevant to lexing
NEWLINE = "\n"
DECIMAL = "."
SENTINEL = "\0"
UNDERSCORE = "_"
COMMENT = "#"
STRING = '"'

SYMBOLS = {
        #single-char tokens
    '+': TokenType.T_PLUS,
    '-': TokenType.T_MINUS,
    '*': TokenType.T_ASTERISK,
    '/': TokenType.T_SLASH,
    '=': TokenType.T_ASSIGN,
    '!': TokenType.T_NEGATE,

    #grouping and punctuation
    '(': TokenType.T_LPAREN,
    ')': TokenType.T_RPAREN,
    '{': TokenType.T_LBRACE,
    '}': TokenType.T_RBRACE,
    '[': TokenType.T_LBRACKET,
    ']': TokenType.T_RBRACKET,
    '"': TokenType.T_STRING,
    ',': TokenType.T_COMMA,

    #double characters
    '+=': TokenType.T_PLUS_ASSIGN,
    '-=': TokenType.T_MINUS_ASSIGN,
    '*=': TokenType.T_ASTERISK_ASSIGN,
    '/=': TokenType.T_SLASH_ASSIGN,

    '==': TokenType.T_EQ,
    '!=': TokenType.T_NEQ,
    '<':  TokenType.T_LT,
    '<=': TokenType.T_LEQ,
    '>':  TokenType.T_GT,
    '>=': TokenType.T_GTEQ,
    '//': TokenType.T_DSLASH,
    '**': TokenType.T_EXPO,
    "&&": TokenType.T_AND,
    "||": TokenType.T_OR,
    "in": TokenType.T_IN
    }

KEYWORDS = {
    # notice most keywords are control flow
    'if': TokenType.T_IF,
    'elif': TokenType.T_ELIF,
    'else': TokenType.T_ELSE,
    'for': TokenType.T_FOR,
    'while': TokenType.T_WHILE,
    'break': TokenType.T_BREAK,
    'continue': TokenType.T_CONTINUE,
    'return': TokenType.T_RETURN,
    "end": TokenType.T_END,
    "fn": TokenType.T_FN,
    }