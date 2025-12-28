from dataclasses import dataclass
from enum import IntEnum


class TokenType(IntEnum):
    # Single-character tokens
    T_PLUS = 1  # +
    T_MINUS = 2  # -
    T_ASTERISK = 3  # *
    T_SLASH = 4  # /
    T_ASSIGN = 5  # =
    T_NEGATE = 6  # !

    # these unary tokens will not be
    # created in the lexer, but will
    # we useful for elegantly remapping
    # expressions into their unambiguous
    # versions, with unary support
    T_UPLUS = 7  # +1, +1.2
    T_UMINUS = 8  # -1, -2.2

    # Grouping & Punctuation
    T_LPAREN = 9  # (
    T_RPAREN = 10  # )
    T_LBRACE = 11  # {
    T_RBRACE = 12  # }
    T_LBRACKET = 13  # [
    T_RBRACKET = 14  # ]
    T_COMMA = 15  # ,
    T_SEMICOLON = 16  # ;
    T_DOT = 17  # .

    # Double-character tokens
    T_PLUS_ASSIGN = 18  # +=
    T_MINUS_ASSIGN = 19  # -=
    T_ASTERISK_ASSIGN = 20  # *=
    T_SLASH_ASSIGN = 21  # /=

    T_EQ = 22  # ==
    T_NEQ = 23  # !=
    T_LT = 24  # <
    T_LEQ = 25  # <=
    T_GT = 26  # >
    T_GTEQ = 27  # >=
    T_DSLASH = 28  # //
    T_EXPO = 29  # **
    T_AND = 30  # &&
    T_OR = 31  # ||

    # Literals
    T_NONE = 32  # none
    T_INT = 33  # 1, 2, 3, ...
    T_FLOAT = 34  # 1.1, 2.2, 3.3, ...
    T_BOOL = 35  # true/false
    T_STRING = 36  # "hi"
    T_IDENT = 37  # my_variable

    # Keywords
    T_IF = 38  # if
    T_ELIF = 39  # elif
    T_ELSE = 40  # else
    T_FOR = 41  # for
    T_WHILE = 42  # while
    T_BREAK = 43  # break
    T_CONTINUE = 44  # continue
    T_RETURN = 45  # return
    T_END = 46  # end
    T_FN = 47  # fn
    T_IN = 48  # in
    T_DATA = 49  # data


T_PLUS_ENUM_VAL = TokenType.T_PLUS.value  # +
T_MINUS_ENUM_VAL = TokenType.T_MINUS.value  # -
T_ASTERISK_ENUM_VAL = TokenType.T_ASTERISK.value  # *
T_SLASH_ENUM_VAL = TokenType.T_SLASH.value  # /
T_ASSIGN_ENUM_VAL = TokenType.T_ASSIGN.value  # =
T_NEGATE_ENUM_VAL = TokenType.T_NEGATE.value  # !

# these unary tokens will not be
# created in the lexer, but will
# we useful for elegantly remapping
# expressions into their unambiguous
# versions, with unary support
T_UPLUS_ENUM_VAL = TokenType.T_UPLUS.value  # +1, +1.2
T_UMINUS_ENUM_VAL = TokenType.T_UMINUS.value  # -1, -2.2

# Grouping & Punctuation
T_LPAREN_ENUM_VAL = TokenType.T_LPAREN.value  # (
T_RPAREN_ENUM_VAL = TokenType.T_RPAREN.value  # )
T_LBRACE_ENUM_VAL = TokenType.T_LBRACE.value  # {
T_RBRACE_ENUM_VAL = TokenType.T_RBRACE.value  # }
T_LBRACKET_ENUM_VAL = TokenType.T_LBRACKET.value  # [
T_RBRACKET_ENUM_VAL = TokenType.T_RBRACKET.value  # ]
T_COMMA_ENUM_VAL = TokenType.T_COMMA.value  # ,
T_SEMICOLON_ENUM_VAL = TokenType.T_SEMICOLON.value  # ;
T_DOT_ENUM_VAL = TokenType.T_DOT.value  # .

# Double-character tokens
T_PLUS_ASSIGN_ENUM_VAL = TokenType.T_PLUS_ASSIGN.value  # +=
T_MINUS_ASSIGN_ENUM_VAL = TokenType.T_MINUS_ASSIGN.value  # -=
T_ASTERISK_ASSIGN_ENUM_VAL = TokenType.T_ASTERISK_ASSIGN.value  # *=
T_SLASH_ASSIGN_ENUM_VAL = TokenType.T_SLASH_ASSIGN.value  # /=

T_EQ_ENUM_VAL = TokenType.T_EQ.value  # ==
T_NEQ_ENUM_VAL = TokenType.T_NEQ.value  # !=
T_LT_ENUM_VAL = TokenType.T_LT.value  # <
T_LEQ_ENUM_VAL = TokenType.T_LEQ.value  # <=
T_GT_ENUM_VAL = TokenType.T_GT.value  # >
T_GTEQ_ENUM_VAL = TokenType.T_GTEQ.value  # >=
T_DSLASH_ENUM_VAL = TokenType.T_DSLASH.value  # //
T_EXPO_ENUM_VAL = TokenType.T_EXPO.value  # **
T_AND_ENUM_VAL = TokenType.T_AND.value  # &&
T_OR_ENUM_VAL = TokenType.T_OR.value  # ||

# Literals
T_NONE_ENUM_VAL = TokenType.T_NONE.value  # none
T_INT_ENUM_VAL = TokenType.T_INT.value  # 1, 2, 3, ...
T_FLOAT_ENUM_VAL = TokenType.T_FLOAT.value  # 1.1, 2.2, 3.3, ...
T_BOOL_ENUM_VAL = TokenType.T_BOOL.value  # true/false
T_STRING_ENUM_VAL = TokenType.T_STRING.value  # "hi"
T_IDENT_ENUM_VAL = TokenType.T_IDENT.value  # my_variable

# Keywords
T_IF_ENUM_VAL = TokenType.T_IF.value  # if
T_ELIF_ENUM_VAL = TokenType.T_ELIF.value  # elif
T_ELSE_ENUM_VAL = TokenType.T_ELSE.value  # else
T_FOR_ENUM_VAL = TokenType.T_FOR.value  # for
T_WHILE_ENUM_VAL = TokenType.T_WHILE.value  # while
T_BREAK_ENUM_VAL = TokenType.T_BREAK.value  # break
T_CONTINUE_ENUM_VAL = TokenType.T_CONTINUE.value  # continue
T_RETURN_ENUM_VAL = TokenType.T_RETURN.value  # return
T_END_ENUM_VAL = TokenType.T_END.value  # end
T_FN_ENUM_VAL = TokenType.T_FN.value  # fn
T_IN_ENUM_VAL = TokenType.T_IN.value  # in
T_DATA_ENUM_VAL = TokenType.T_DATA.value  # data


@dataclass(slots=True)
class Lexeme:
    # dataclass for representing a single token of input after lexical analysis
    type_enum_id: int
    value: str
    line: int
    column_start: int
    column_end: int

    def __repr__(self):
        return f"""Lexeme(\n
        {self.value},\n
        {self.line}, \n
        {self.column_start},\n
        {self.column_end}\n
        )
        """


# these constants aren't tokens but relevant to lexing
NEWLINE = "\n"
DECIMAL = "."
SENTINEL = "\0"
UNDERSCORE = "_"
COMMENT = "#"
STRING = '"'

SYMBOLS = {
    # single-char tokens
    "+": T_PLUS_ENUM_VAL,
    "-": T_MINUS_ENUM_VAL,
    "*": T_ASTERISK_ENUM_VAL,
    "/": T_SLASH_ENUM_VAL,
    "=": T_ASSIGN_ENUM_VAL,
    "!": T_NEGATE_ENUM_VAL,
    # grouping and punctuation
    "(": T_LPAREN_ENUM_VAL,
    ")": T_RPAREN_ENUM_VAL,
    "{": T_LBRACE_ENUM_VAL,
    "}": T_RBRACE_ENUM_VAL,
    "[": T_LBRACKET_ENUM_VAL,
    "]": T_RBRACKET_ENUM_VAL,
    '"': T_STRING_ENUM_VAL,
    ",": T_COMMA_ENUM_VAL,
    ";": T_SEMICOLON_ENUM_VAL,
    # double characters
    "+=": T_PLUS_ASSIGN_ENUM_VAL,
    "-=": T_MINUS_ASSIGN_ENUM_VAL,
    "*=": T_ASTERISK_ASSIGN_ENUM_VAL,
    "/=": T_SLASH_ASSIGN_ENUM_VAL,
    "==": T_EQ_ENUM_VAL,
    "!=": T_NEQ_ENUM_VAL,
    "<": T_LT_ENUM_VAL,
    "<=": T_LEQ_ENUM_VAL,
    ">": T_GT_ENUM_VAL,
    ">=": T_GTEQ_ENUM_VAL,
    "//": T_DSLASH_ENUM_VAL,
    "**": T_EXPO_ENUM_VAL,
    "&&": T_AND_ENUM_VAL,
    "||": T_OR_ENUM_VAL,
    "in": T_IN_ENUM_VAL,
}

KEYWORDS = {
    # notice most keywords are control flow
    "if": T_IF_ENUM_VAL,
    "elif": T_ELIF_ENUM_VAL,
    "else": T_ELSE_ENUM_VAL,
    "for": T_FOR_ENUM_VAL,
    "while": T_WHILE_ENUM_VAL,
    "break": T_BREAK_ENUM_VAL,
    "continue": T_CONTINUE_ENUM_VAL,
    "return": T_RETURN_ENUM_VAL,
    "end": T_END_ENUM_VAL,
    "fn": T_FN_ENUM_VAL,
    "data": T_DATA_ENUM_VAL,
}
