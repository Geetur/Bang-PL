# after this we are guaranteed to have every expression converted into an AST
# and every line construct such as if, elif, fn, converted into its respective
# node. line-wise, the program is syntactically valid

from math import isfinite

from bang.lexing.lexer_tokens import (
    T_AND_ENUM_VAL,
    T_ASSIGN_ENUM_VAL,
    T_ASTERISK_ASSIGN_ENUM_VAL,
    T_ASTERISK_ENUM_VAL,
    T_BOOL_ENUM_VAL,
    T_BREAK_ENUM_VAL,
    T_COMMA_ENUM_VAL,
    T_CONTINUE_ENUM_VAL,
    T_DATA_ENUM_VAL,
    T_DOT_ENUM_VAL,
    T_DSLASH_ENUM_VAL,
    T_ELIF_ENUM_VAL,
    T_ELSE_ENUM_VAL,
    T_END_ENUM_VAL,
    T_EQ_ENUM_VAL,
    T_EXPO_ENUM_VAL,
    T_FLOAT_ENUM_VAL,
    T_FN_ENUM_VAL,
    T_FOR_ENUM_VAL,
    T_GT_ENUM_VAL,
    T_GTEQ_ENUM_VAL,
    T_IDENT_ENUM_VAL,
    T_IF_ENUM_VAL,
    T_IN_ENUM_VAL,
    T_INT_ENUM_VAL,
    T_LBRACE_ENUM_VAL,
    T_LBRACKET_ENUM_VAL,
    T_LEQ_ENUM_VAL,
    T_LPAREN_ENUM_VAL,
    T_LT_ENUM_VAL,
    T_MINUS_ASSIGN_ENUM_VAL,
    T_MINUS_ENUM_VAL,
    T_NEGATE_ENUM_VAL,
    T_NEQ_ENUM_VAL,
    T_NONE_ENUM_VAL,
    T_OR_ENUM_VAL,
    T_PLUS_ASSIGN_ENUM_VAL,
    T_PLUS_ENUM_VAL,
    T_RBRACE_ENUM_VAL,
    T_RBRACKET_ENUM_VAL,
    T_RETURN_ENUM_VAL,
    T_RPAREN_ENUM_VAL,
    T_SEMICOLON_ENUM_VAL,
    T_SLASH_ASSIGN_ENUM_VAL,
    T_SLASH_ENUM_VAL,
    T_STRING_ENUM_VAL,
    T_UMINUS_ENUM_VAL,
    T_UPLUS_ENUM_VAL,
    T_WHILE_ENUM_VAL,
    TokenType,
)
from bang.parsing.parser_nodes import (
    ARRAY_LITERAL_NODE_CLASS,
    ASSIGNMENT_NODE_CLASS,
    BIN_OP_NODE_CLASS,
    BOOLEAN_LITERAL_NODE_CLASS,
    BREAK_NODE_CLASS,
    CALL_NODE_CLASS,
    CONTINUE_NODE_CLASS,
    DATA_CLASS_NODE_CLASS,
    ELIF_NODE_CLASS,
    ELSE_NODE_CLASS,
    END_NODE_CLASS,
    EXPRESSION_NODE_CLASS,
    FIELD_ACCESS_NODE_CLASS,
    FLOAT_LITERAL_NODE_CLASS,
    FOR_NODE_CLASS,
    FUNCTION_NODE_CLASS,
    IDENTIFIER_NODE_CLASS,
    IF_NODE_CLASS,
    INDEX_NODE_CLASS,
    INTEGER_LITERAL_NODE_CLASS,
    NONE_LITERAL_NODE_CLASS,
    ParameterNode,
    RETURN_NODE_CLASS,
    STRING_LITERAL_NODE_CLASS,
    UNARY_OP_NODE_CLASS,
    WHILE_NODE_CLASS,
)


class ParserError(Exception):
    def __init__(self, text, msg, row, start, end):
        self.text = text
        self.msg = msg
        self.row = row
        self.start = start
        self.end = end

        super().__init__(self._format())

    def _get_real_error_line(self):
        lines = self.text.splitlines()
        # Row is 1-based in tokens, so -1 for index
        if 0 <= self.row - 1 < len(lines):
            return lines[self.row - 1]
        return ""

    def _format(self):
        error_line = self._get_real_error_line()
        crt_length = max(1, self.end - self.start)
        pointers = " " * (self.start - 1) + "^" * crt_length
        return (
            f"[ParserError] Line {self.row}, Column {self.start}-{self.end}:\n"
            f"{error_line.rstrip()}\n"
            f"{pointers}\n"
            f"{self.msg}"
        )

    def __str__(self) -> str:
        return self._format()

    __repr__ = __str__


class TokenSpan:
    """A constant-time view into a token sequence, including sliced subranges."""

    __slots__ = ("tokens", "start", "stop")

    def __init__(self, tokens, start=0, stop=None):
        self.tokens = tokens
        self.start = start
        self.stop = len(tokens) if stop is None else stop

    def __len__(self):
        return self.stop - self.start

    def __getitem__(self, key):
        if isinstance(key, slice):
            start, stop, step = key.indices(len(self))
            if step != 1:
                return [self[index] for index in range(start, stop, step)]
            return TokenSpan(self.tokens, self.start + start, self.start + max(start, stop))
        if key < 0:
            key += len(self)
        if not 0 <= key < len(self):
            raise IndexError(key)
        return self.tokens[self.start + key]

    def __iter__(self):
        for index in range(self.start, self.stop):
            yield self.tokens[index]


def _numeric_literal(token, convert, node_type):
    try:
        if convert is int and len(token.value) > 4300:
            raise ValueError("integer literal exceeds 4300 digits")
        value = convert(token.value)
        if isinstance(value, float) and not isfinite(value):
            raise ValueError("non-finite literal")
    except (ValueError, OverflowError) as error:
        raise ParserError(
            "",
            "numeric literal is invalid or too large",
            token.line,
            token.column_start,
            token.column_end,
        ) from error
    return node_type(value, token)


class ExpressionParser:
    MAX_EXPRESSION_DEPTH = 64

    PRECEDENCE_TABLE = []
    ASSOC_TABLE = []  # 0 = Left, 1 = Right

    ARRAY_LITERAL_NODE_CLASS = ARRAY_LITERAL_NODE_CLASS
    ASSIGNMENT_NODE_CLASS = ASSIGNMENT_NODE_CLASS
    BIN_OP_NODE_CLASS = BIN_OP_NODE_CLASS
    BOOLEAN_LITERAL_NODE_CLASS = BOOLEAN_LITERAL_NODE_CLASS
    BREAK_NODE_CLASS = BREAK_NODE_CLASS
    CALL_NODE_CLASS = CALL_NODE_CLASS
    CONTINUE_NODE_CLASS = CONTINUE_NODE_CLASS
    DATA_CLASS_NODE_CLASS = DATA_CLASS_NODE_CLASS
    ELIF_NODE_CLASS = ELIF_NODE_CLASS
    ELSE_NODE_CLASS = ELSE_NODE_CLASS
    END_NODE_CLASS = END_NODE_CLASS
    EXPRESSION_NODE_CLASS = EXPRESSION_NODE_CLASS
    FIELD_ACCESS_NODE_CLASS = FIELD_ACCESS_NODE_CLASS
    FLOAT_LITERAL_NODE_CLASS = FLOAT_LITERAL_NODE_CLASS
    FOR_NODE_CLASS = FOR_NODE_CLASS
    FUNCTION_NODE_CLASS = FUNCTION_NODE_CLASS
    IDENTIFIER_NODE_CLASS = IDENTIFIER_NODE_CLASS
    IF_NODE_CLASS = IF_NODE_CLASS
    INDEX_NODE_CLASS = INDEX_NODE_CLASS
    INTEGER_LITERAL_NODE_CLASS = INTEGER_LITERAL_NODE_CLASS
    NONE_LITERAL_NODE_CLASS = NONE_LITERAL_NODE_CLASS
    RETURN_NODE_CLASS = RETURN_NODE_CLASS
    STRING_LITERAL_NODE_CLASS = STRING_LITERAL_NODE_CLASS
    UNARY_OP_NODE_CLASS = UNARY_OP_NODE_CLASS
    WHILE_NODE_CLASS = WHILE_NODE_CLASS

    # ENUM MATCHES
    T_PLUS_ENUM_VAL = T_PLUS_ENUM_VAL  # +
    T_MINUS_ENUM_VAL = T_MINUS_ENUM_VAL  # -
    T_ASTERISK_ENUM_VAL = T_ASTERISK_ENUM_VAL  # *
    T_SLASH_ENUM_VAL = T_SLASH_ENUM_VAL  # /
    T_ASSIGN_ENUM_VAL = T_ASSIGN_ENUM_VAL  # =
    T_NEGATE_ENUM_VAL = T_NEGATE_ENUM_VAL  # !

    # these unary tokens will not be
    # created in the lexer, but will
    # we useful for elegantly remapping
    # expressions into their unambiguous
    # versions, with unary support
    T_UPLUS_ENUM_VAL = T_UPLUS_ENUM_VAL  # +1, +1.2
    T_UMINUS_ENUM_VAL = T_UMINUS_ENUM_VAL  # -1, -2.2

    # Grouping & Punctuation
    T_LPAREN_ENUM_VAL = T_LPAREN_ENUM_VAL  # (
    T_RPAREN_ENUM_VAL = T_RPAREN_ENUM_VAL  # )
    T_LBRACE_ENUM_VAL = T_LBRACE_ENUM_VAL  # {
    T_RBRACE_ENUM_VAL = T_RBRACE_ENUM_VAL  # }
    T_LBRACKET_ENUM_VAL = T_LBRACKET_ENUM_VAL  # [
    T_RBRACKET_ENUM_VAL = T_RBRACKET_ENUM_VAL  # ]
    T_COMMA_ENUM_VAL = T_COMMA_ENUM_VAL  # ,
    T_SEMICOLON_ENUM_VAL = T_SEMICOLON_ENUM_VAL  # ;
    T_DOT_ENUM_VAL = T_DOT_ENUM_VAL  # .

    # Double-character tokens
    T_PLUS_ASSIGN_ENUM_VAL = T_PLUS_ASSIGN_ENUM_VAL  # +=
    T_MINUS_ASSIGN_ENUM_VAL = T_MINUS_ASSIGN_ENUM_VAL  # -=
    T_ASTERISK_ASSIGN_ENUM_VAL = T_ASTERISK_ASSIGN_ENUM_VAL  # *=
    T_SLASH_ASSIGN_ENUM_VAL = T_SLASH_ASSIGN_ENUM_VAL  # /=

    T_EQ_ENUM_VAL = T_EQ_ENUM_VAL  # ==
    T_NEQ_ENUM_VAL = T_NEQ_ENUM_VAL  # !=
    T_LT_ENUM_VAL = T_LT_ENUM_VAL  # <
    T_LEQ_ENUM_VAL = T_LEQ_ENUM_VAL  # <=
    T_GT_ENUM_VAL = T_GT_ENUM_VAL  # >
    T_GTEQ_ENUM_VAL = T_GTEQ_ENUM_VAL  # >=
    T_DSLASH_ENUM_VAL = T_DSLASH_ENUM_VAL  # //
    T_EXPO_ENUM_VAL = T_EXPO_ENUM_VAL  # **
    T_AND_ENUM_VAL = T_AND_ENUM_VAL  # &&
    T_OR_ENUM_VAL = T_OR_ENUM_VAL  # ||

    # Literals
    T_NONE_ENUM_VAL = T_NONE_ENUM_VAL  # none
    T_INT_ENUM_VAL = T_INT_ENUM_VAL  # 1, 2, 3, ...
    T_FLOAT_ENUM_VAL = T_FLOAT_ENUM_VAL  # 1.1, 2.2, 3.3, ...
    T_BOOL_ENUM_VAL = T_BOOL_ENUM_VAL  # true/false
    T_STRING_ENUM_VAL = T_STRING_ENUM_VAL  # "hi"
    T_IDENT_ENUM_VAL = T_IDENT_ENUM_VAL  # my_variable

    # Keywords
    T_IF_ENUM_VAL = T_IF_ENUM_VAL  # if
    T_ELIF_ENUM_VAL = T_ELIF_ENUM_VAL  # elif
    T_ELSE_ENUM_VAL = T_ELSE_ENUM_VAL  # else
    T_FOR_ENUM_VAL = T_FOR_ENUM_VAL  # for
    T_WHILE_ENUM_VAL = T_WHILE_ENUM_VAL  # while
    T_BREAK_ENUM_VAL = T_BREAK_ENUM_VAL  # break
    T_CONTINUE_ENUM_VAL = T_CONTINUE_ENUM_VAL  # continue
    T_RETURN_ENUM_VAL = T_RETURN_ENUM_VAL  # return
    T_END_ENUM_VAL = T_END_ENUM_VAL  # end
    T_FN_ENUM_VAL = T_FN_ENUM_VAL  # fn
    T_IN_ENUM_VAL = T_IN_ENUM_VAL  # in
    T_DATA_ENUM_VAL = T_DATA_ENUM_VAL  # data

    # 1) Precedence (higher = tighter binding)
    PRECEDENCE = {
        # assignments & compound-assign
        # logical
        T_OR_ENUM_VAL: 2,  # ||
        T_AND_ENUM_VAL: 3,  # &&
        # equality
        T_EQ_ENUM_VAL: 4,  # ==
        T_NEQ_ENUM_VAL: 4,  # !=
        T_IN_ENUM_VAL: 4,
        # relational
        T_LT_ENUM_VAL: 5,  # <
        T_LEQ_ENUM_VAL: 5,  # <=
        T_GT_ENUM_VAL: 5,  # >
        T_GTEQ_ENUM_VAL: 5,  # >=
        # additive
        T_PLUS_ENUM_VAL: 6,  # +
        T_MINUS_ENUM_VAL: 6,  # -
        # multiplicative
        T_ASTERISK_ENUM_VAL: 7,  # *
        T_SLASH_ENUM_VAL: 7,  # /
        T_DSLASH_ENUM_VAL: 7,  # //
        # exponent
        T_EXPO_ENUM_VAL: 8,  # **
        # unary
        T_NEGATE_ENUM_VAL: 9,  # !
        T_UPLUS_ENUM_VAL: 9,
        T_UMINUS_ENUM_VAL: 9,
        T_DOT_ENUM_VAL: 10,
    }

    # you can technically handle assignments within the SYA
    # but in the spirit or our parser, anything other than expressions
    # with be thrust into a seperate modular function
    ASSOCIATIVITY = {
        # right-assoc
        **{
            op: "right"
            for op in (
                T_UPLUS_ENUM_VAL,
                T_UMINUS_ENUM_VAL,
                T_EXPO_ENUM_VAL,
                T_NEGATE_ENUM_VAL,
            )
        },
        # left-assoc
        **{
            op: "left"
            for op in (
                T_OR_ENUM_VAL,
                T_AND_ENUM_VAL,
                T_EQ_ENUM_VAL,
                T_NEQ_ENUM_VAL,
                T_LT_ENUM_VAL,
                T_LEQ_ENUM_VAL,
                T_GT_ENUM_VAL,
                T_GTEQ_ENUM_VAL,
                T_PLUS_ENUM_VAL,
                T_MINUS_ENUM_VAL,
                T_ASTERISK_ENUM_VAL,
                T_SLASH_ENUM_VAL,
                T_DSLASH_ENUM_VAL,
                T_IN_ENUM_VAL,
                T_DOT_ENUM_VAL,
            )
        },
    }
    ASSIGNMENT = {
        T_ASSIGN_ENUM_VAL,
        T_PLUS_ASSIGN_ENUM_VAL,
        T_MINUS_ASSIGN_ENUM_VAL,
        T_SLASH_ASSIGN_ENUM_VAL,
        T_ASTERISK_ASSIGN_ENUM_VAL,
    }

    DEPTH_CREATORS = {
        T_LBRACKET_ENUM_VAL: T_RBRACKET_ENUM_VAL,
        T_LBRACE_ENUM_VAL: T_RBRACE_ENUM_VAL,
    }

    DEPTH_ENDERS = (T_RBRACKET_ENUM_VAL, T_RBRACE_ENUM_VAL)

    UNARY_OPS = {T_UPLUS_ENUM_VAL, T_UMINUS_ENUM_VAL, T_NEGATE_ENUM_VAL}

    BINARY_TO_UNARY_OP = {
        T_PLUS_ENUM_VAL: T_UPLUS_ENUM_VAL,
        T_MINUS_ENUM_VAL: T_UMINUS_ENUM_VAL,
        T_NEGATE_ENUM_VAL: T_NEGATE_ENUM_VAL,
    }

    CAN_FOLLOW_OPERATOR = {
        T_INT_ENUM_VAL,
        T_FLOAT_ENUM_VAL,
        T_BOOL_ENUM_VAL,
        T_NONE_ENUM_VAL,
        T_IDENT_ENUM_VAL,
        T_LBRACKET_ENUM_VAL,
        T_LPAREN_ENUM_VAL,
        T_UMINUS_ENUM_VAL,
        T_UPLUS_ENUM_VAL,
        T_NEGATE_ENUM_VAL,
        T_STRING_ENUM_VAL,
    }

    # can_follow is a really elegant way to handle errors in the shunting yard algorithm
    # we essentially define a two-state transition, and based on our
    # current state we can either allow the next token, or throw an error
    # another important aspect to this transition is that not every operand expects an operator
    # whereas every operator expects an operand and so you can define an additional table
    # or information that defines each operand with a true or false value to determine whether
    # it merits a state transition, but there are so few you can typically just if statement

    CAN_FOLLOW_OPERAND = (set(PRECEDENCE) - UNARY_OPS) | {
        T_RPAREN_ENUM_VAL,
        T_RBRACKET_ENUM_VAL,
        # this can follow an operand because in the case an array
        # follows an operand it can be an index node
        # if the operand isn't indexable we throw and error in the index handler
        T_LBRACKET_ENUM_VAL,
        T_LBRACE_ENUM_VAL,
        T_RBRACE_ENUM_VAL,
        T_DOT_ENUM_VAL,
    }

    # these are literals that can be instantly determined, unlike
    # arrays which must be determined over n tokens
    LITERAL_MAP = {
        T_INT_ENUM_VAL: lambda tok: _numeric_literal(tok, int, INTEGER_LITERAL_NODE_CLASS),
        T_FLOAT_ENUM_VAL: lambda tok: _numeric_literal(tok, float, FLOAT_LITERAL_NODE_CLASS),
        T_BOOL_ENUM_VAL: lambda tok: BOOLEAN_LITERAL_NODE_CLASS(
            (True if tok.value == "true" else False), tok
        ),
        T_NONE_ENUM_VAL: lambda tok: NONE_LITERAL_NODE_CLASS(tok.value, tok),
        T_STRING_ENUM_VAL: lambda tok: STRING_LITERAL_NODE_CLASS(tok.value, tok),
    }

    NOT_INDEXABLE = (
        INTEGER_LITERAL_NODE_CLASS,
        FLOAT_LITERAL_NODE_CLASS,
        NONE_LITERAL_NODE_CLASS,
        BOOLEAN_LITERAL_NODE_CLASS,
    )

    VALID_LEFT_HANDS = (
        INDEX_NODE_CLASS,
        IDENTIFIER_NODE_CLASS,
        ARRAY_LITERAL_NODE_CLASS,
        FIELD_ACCESS_NODE_CLASS,
    )

    SINGLE_TOKEN_TO_CLASS = {
        T_END_ENUM_VAL: END_NODE_CLASS,
        T_BREAK_ENUM_VAL: BREAK_NODE_CLASS,
        T_CONTINUE_ENUM_VAL: CONTINUE_NODE_CLASS,
    }

    @classmethod
    def _init_type_tables(cls):
        max_id = max(t.value for t in TokenType) + 1

        cls.IS_ASSIGN = [False] * max_id
        cls.IS_BIN2UN = [False] * max_id
        cls.CAN_OPND = [False] * max_id
        cls.CAN_OPR = [False] * max_id
        cls.IS_UNARY = [False] * max_id
        cls.IS_LITERAL = [False] * max_id

        for t in TokenType:
            v = t.value
            cls.IS_ASSIGN[v] = v in cls.ASSIGNMENT
            cls.IS_BIN2UN[v] = v in cls.BINARY_TO_UNARY_OP
            cls.CAN_OPND[v] = v in cls.CAN_FOLLOW_OPERAND
            cls.CAN_OPR[v] = v in cls.CAN_FOLLOW_OPERATOR
            cls.IS_UNARY[v] = v in cls.UNARY_OPS
            cls.IS_LITERAL[v] = v in cls.LITERAL_MAP

    def __init__(self, tokens, file):
        self.file = file
        self.tokens = tokens
        self.post_split = []
        self.post_SYA = []
        self.illegal_assignment = 0
        self.expression_depth = 0

    def split(self):
        """Split logical statements, continuing newlines inside balanced delimiters."""
        if getattr(self.__class__, "IS_ASSIGN", None) is None:
            self.__class__._init_type_tables()
        statements = []
        current = []
        openings = []
        previous_line = None
        pairs = {
            self.T_LPAREN_ENUM_VAL: self.T_RPAREN_ENUM_VAL,
            self.T_LBRACKET_ENUM_VAL: self.T_RBRACKET_ENUM_VAL,
            self.T_LBRACE_ENUM_VAL: self.T_RBRACE_ENUM_VAL,
        }
        enders = set(pairs.values())
        closing_text = {"(": ")", "[": "]", "{": "}"}

        for tok in self.tokens:
            typ = tok.type_enum_id
            if tok.line != previous_line and not openings and current:
                statements.append(current)
                current = []
            previous_line = tok.line

            if typ == self.T_SEMICOLON_ENUM_VAL:
                if openings:
                    self._syntax_error("';' is only allowed outside expression delimiters", tok)
                if current:
                    statements.append(current)
                    current = []
                continue

            if typ in pairs:
                openings.append(tok)
            elif typ in enders:
                if not openings:
                    self._syntax_error(f"unexpected closing delimiter {tok.value!r}", tok)
                opening = openings[-1]
                if typ != pairs[opening.type_enum_id]:
                    self._syntax_error(
                        f"mismatched closing delimiter {tok.value!r}; "
                        f"expected {closing_text[opening.value]!r} to close "
                        f"{opening.value!r} from line {opening.line}",
                        tok,
                    )
                openings.pop()
            current.append(tok)

        if openings:
            opening = openings[-1]
            self._syntax_error(
                f"unclosed delimiter {opening.value!r}; expected {closing_text[opening.value]!r}",
                opening,
            )
        if current:
            statements.append(current)
        self.post_split = statements
        return self.post_split

    # most constructs in this lang follow wildy different layouts (sometimes very unique)
    # and so to avoid creating a single parsing algo that can handle all of these different
    # constructs, it's easier to handle each singular construct different, and allow
    # them to interweave with eachother to create a legible Node
    def loading_into_algos(self):
        for line_idx, line in enumerate(self.post_split):
            self.illegal_assignment = 0
            if not line:
                continue

            first = line[0]
            first_type_id = first.type_enum_id

            # keyword constructs must start the line, so check only first token
            if first_type_id in (self.T_IF_ENUM_VAL, self.T_ELIF_ENUM_VAL, self.T_ELSE_ENUM_VAL):
                self.handle_if_else_condition(line_idx)
                continue
            if first_type_id == self.T_FOR_ENUM_VAL:
                self.handle_for_loop(line_idx)
                continue
            if first_type_id == self.T_WHILE_ENUM_VAL:
                self.handle_while_loop(line_idx)
                continue
            if first_type_id in (
                self.T_BREAK_ENUM_VAL,
                self.T_CONTINUE_ENUM_VAL,
                self.T_END_ENUM_VAL,
            ):
                self.handle_single_tokens(line_idx)
                continue
            if first_type_id == self.T_FN_ENUM_VAL:
                self.handle_function_def(line_idx)
                continue
            if first_type_id == self.T_DATA_ENUM_VAL:
                self.handle_dataclass_def(line_idx)
                continue
            if first_type_id == self.T_RETURN_ENUM_VAL:
                self.handle_return(line_idx)
                continue

            # Assignment is a statement, never a side effect of parsing a subexpression.
            depth = 0
            assignment = None
            for index, token in enumerate(line):
                typ = token.type_enum_id
                if typ in (
                    self.T_LPAREN_ENUM_VAL,
                    self.T_LBRACKET_ENUM_VAL,
                    self.T_LBRACE_ENUM_VAL,
                ):
                    depth += 1
                elif typ in (
                    self.T_RPAREN_ENUM_VAL,
                    self.T_RBRACKET_ENUM_VAL,
                    self.T_RBRACE_ENUM_VAL,
                ):
                    depth -= 1
                elif self.IS_ASSIGN[typ] and depth == 0:
                    if assignment is not None:
                        raise ParserError(
                            self.file,
                            "chained assignment is not supported",
                            token.line,
                            token.column_start,
                            token.column_end,
                        )
                    assignment = index
            if assignment is not None:
                self.handle_assignments(TokenSpan(line), assignment)
                continue
            expr = self.shunting_yard_algo(line)
            if expr is not None:
                self.post_SYA.append(expr)

        return self.post_SYA

    def handle_if_else_condition(self, line_idx):
        line = self.post_split[line_idx]
        if_token = line[0]
        if_token_id = if_token.type_enum_id

        # handling the else keyword seperately for the if and elif
        # since it follows different syntax than the if-elif constructs
        if if_token_id == self.T_ELSE_ENUM_VAL:
            if len(line) != 1:
                raise ParserError(
                    self.file,
                    "else must appear alone in its statement",
                    if_token.line,
                    if_token.column_start,
                    if_token.column_end,
                )
            else_node = self.ELSE_NODE_CLASS(meta_data=if_token)
            self.post_SYA.append(else_node)
        else:
            if len(line) < 2:
                raise ParserError(
                    self.file,
                    "if statement syntax is '[if][some expression]'",
                    if_token.line,
                    if_token.column_start,
                    if_token.column_end,
                )

            expected_expression = line[1:]

            expr_node = self.shunting_yard_algo(expected_expression)

            if_node = (
                self.IF_NODE_CLASS(condition=expr_node, meta_data=if_token)
                if if_token_id == T_IF_ENUM_VAL
                else self.ELIF_NODE_CLASS(condition=expr_node, meta_data=if_token)
            )

            self.post_SYA.append(if_node)

    def handle_for_loop(self, line_idx):
        line = self.post_split[line_idx]
        for_token = line[0]
        message = "for loop syntax is 'for name expression' or 'for [targets] expression'"
        if len(line) < 3:
            self._syntax_error(message, for_token)

        variable_token = line[1]
        if variable_token.type_enum_id == self.T_IDENT_ENUM_VAL:
            variable_node = self.IDENTIFIER_NODE_CLASS(
                value=variable_token.value, meta_data=variable_token
            )
            bound_start = 2
        elif variable_token.type_enum_id == self.T_LBRACKET_ENUM_VAL:
            variable_node, consumed = self.handle_array_literals(TokenSpan(line, 1))
            self._validate_assignment_target(variable_node, variable_token)
            bound_start = consumed + 2
        else:
            self._syntax_error(message, variable_token)

        if bound_start == len(line):
            self._syntax_error("for loop requires an iterable expression", line[-1])
        expr_node = self.shunting_yard_algo(TokenSpan(line, bound_start))

        for_node = self.FOR_NODE_CLASS(
            variable=variable_node, bound=expr_node, meta_data=variable_token
        )

        self.post_SYA.append(for_node)

    def handle_while_loop(self, line_idx):
        line = self.post_split[line_idx]
        while_token = line[0]
        if len(line) < 2:
            raise ParserError(
                self.file,
                "while loop syntax is '[while][some expression]'",
                while_token.line,
                while_token.column_start,
                while_token.column_end,
            )

        expected_expression = line[1:]

        expr_node = self.shunting_yard_algo(expected_expression)

        while_node = self.WHILE_NODE_CLASS(condition=expr_node, meta_data=while_token)

        self.post_SYA.append(while_node)

    def handle_single_tokens(self, line_idx):
        line = self.post_split[line_idx]
        single_token = line[0]

        if len(line) != 1:
            raise ParserError(
                self.file,
                f"{single_token.value} token must exist solely \
                (no other tokens allowed to exist on same line)",
                single_token.line,
                single_token.column_start,
                single_token.column_end,
            )

        single_node = self.SINGLE_TOKEN_TO_CLASS[single_token.type_enum_id]

        single_node_class = single_node(single_token)

        self.post_SYA.append(single_node_class)

    def _syntax_error(self, message, token):
        raise ParserError(self.file, message, token.line, token.column_start, token.column_end)

    def _braced_items(self, line, *, allow_empty=False):
        """Split a brace list while retaining nested token spans and source order."""
        pieces = []
        creators = []
        start = 1
        for position in range(1, len(line)):
            token = line[position]
            typ = token.type_enum_id
            if typ in self.DEPTH_CREATORS:
                creators.append(token)
            elif typ in self.DEPTH_ENDERS:
                if creators:
                    if typ != self.DEPTH_CREATORS[creators[-1].type_enum_id]:
                        self._syntax_error("mismatched brackets", token)
                    creators.pop()
                else:
                    if typ != self.T_RBRACE_ENUM_VAL:
                        self._syntax_error("mismatched brackets", token)
                    if position > start:
                        pieces.append(line[start:position])
                    return pieces, position
            elif typ == self.T_COMMA_ENUM_VAL and not creators:
                if position == start:
                    if not allow_empty:
                        self._syntax_error("empty parameter declaration", token)
                else:
                    pieces.append(line[start:position])
                start = position + 1
        self._syntax_error("unterminated argument list", line[0])

    def _function_signature(self, line, *, anonymous=False):
        """Parse the shared argument interface and return the first body token."""
        message = "expected a function signature with an argument-array name or {parameters}"
        start = 1 if anonymous else 2
        if not anonymous and (len(line) < 2 or line[1].type_enum_id != self.T_IDENT_ENUM_VAL):
            self._syntax_error("expected a function name", line[0])
        if start >= len(line):
            self._syntax_error(message, line[0])
        variadic_name = None
        if line[start].type_enum_id == self.T_IDENT_ENUM_VAL:
            variadic_name = line[start].value
            start += 1
        parameters = None
        if start < len(line) and line[start].type_enum_id == self.T_LBRACE_ENUM_VAL:
            pieces, consumed = self._braced_items(TokenSpan(line, start))
            start += consumed + 1
            parameters = []
            seen = set() if variadic_name is None else {variadic_name}
            optional = False
            for piece in pieces:
                token = piece[0]
                if token.type_enum_id != self.T_IDENT_ENUM_VAL:
                    self._syntax_error("parameter names must be identifiers", token)
                if token.value in seen:
                    self._syntax_error(f"duplicate parameter '{token.value}'", token)
                seen.add(token.value)
                if len(piece) == 1:
                    if optional:
                        self._syntax_error("required parameters must precede defaults", token)
                    default = None
                elif len(piece) >= 3 and piece[1].type_enum_id == self.T_ASSIGN_ENUM_VAL:
                    default = self.shunting_yard_algo(piece[2:])
                    optional = True
                else:
                    self._syntax_error("expected a parameter name or name = expression", token)
                parameters.append(ParameterNode(token.value, default, token))
            parameters = tuple(parameters)
        elif variadic_name is None:
            self._syntax_error(message, line[0])
        node = self.FUNCTION_NODE_CLASS(
            name=None if anonymous else line[1].value,
            arg_list_name=variadic_name,
            meta_data=line[0],
            parameters=parameters,
        )
        return node, start

    def _short_function_return(self, line, position):
        if position >= len(line) or line[position].type_enum_id != self.T_RETURN_ENUM_VAL:
            token = line[position] if position < len(line) else line[-1]
            self._syntax_error("short functions require 'return' before the body expression", token)
        if position + 1 == len(line):
            self._syntax_error("short function requires a return expression", line[position])
        return self.RETURN_NODE_CLASS(
            meta_data=line[position],
            expression=self.shunting_yard_algo(TokenSpan(line, position + 1)),
        )

    def handle_function_def(self, line_idx):
        line = self.post_split[line_idx]
        node, position = self._function_signature(line)
        self.post_SYA.append(node)
        if position != len(line):
            # Lower a short declaration to the same block AST as its long form.
            self.post_SYA.append(self._short_function_return(line, position))
            self.post_SYA.append(self.END_NODE_CLASS(line[position]))

    def handle_anonymous_function(self, line):
        node, position = self._function_signature(line, anonymous=True)
        # The body extends to the enclosing expression boundary. Its own nested
        # delimiters stay inside the body; a caller's closing parenthesis does not.
        pairs = {
            self.T_LPAREN_ENUM_VAL: self.T_RPAREN_ENUM_VAL,
            self.T_LBRACKET_ENUM_VAL: self.T_RBRACKET_ENUM_VAL,
            self.T_LBRACE_ENUM_VAL: self.T_RBRACE_ENUM_VAL,
        }
        enders = set(pairs.values())
        openings = []
        end = min(position + 1, len(line))
        while end < len(line):
            typ = line[end].type_enum_id
            if not openings and (typ in enders or typ == self.T_COMMA_ENUM_VAL):
                break
            if typ in pairs:
                openings.append(typ)
            elif typ in enders:
                if not openings or pairs[openings[-1]] != typ:
                    self._syntax_error("mismatched function-body delimiter", line[end])
                openings.pop()
            end += 1
        node.body.block.append(self._short_function_return(TokenSpan(line, 0, end), position))
        return node, end

    def handle_dataclass_def(self, line_idx):
        IDENTIFIER_NODE_CLASS = self.IDENTIFIER_NODE_CLASS
        line = self.post_split[line_idx]

        data_keyword_token = line[0]
        if len(line) <= 2:
            raise ParserError(
                self.file,
                "dataclass definition syntax is \
                [data keyword][dataclass name][list of field names]",
                data_keyword_token.line,
                data_keyword_token.column_start,
                data_keyword_token.column_end,
            )

        dataclass_name = line[1]
        if dataclass_name.type_enum_id != self.T_IDENT_ENUM_VAL:
            raise ParserError(
                self.file,
                "dataclass name must be an identifier",
                data_keyword_token.line,
                data_keyword_token.column_start,
                data_keyword_token.column_end,
            )

        list_of_field_names = self.shunting_yard_algo(line[2:])
        # obviously instead of doing two o(n) passes over the
        # elements list we could just do one
        # more complex for loop, but in the vast,
        # vast majority of cases, the dataclass
        # field name list will be less than 20 tokens long, o(20)
        # list comprehensions are pretty fast
        if type(list_of_field_names.root_expr) is not self.ARRAY_LITERAL_NODE_CLASS or (
            any(
                type(i.root_expr) is not IDENTIFIER_NODE_CLASS
                for i in list_of_field_names.root_expr.elements
            )
        ):
            raise ParserError(
                self.file,
                "list of field names must be a list of identifiers",
                data_keyword_token.line,
                data_keyword_token.column_start,
                data_keyword_token.column_end,
            )
        list_of_field_names_raw_values = [
            i.root_expr.value for i in list_of_field_names.root_expr.elements
        ]
        dataclass_node = self.DATA_CLASS_NODE_CLASS(
            dataclass_name.value, list_of_field_names_raw_values, data_keyword_token
        )
        self.post_SYA.append(dataclass_node)

    def handle_function_call(self, line, function_name):
        if type(function_name) in self.LITERAL_MAP or (
            type(function_name) is self.ARRAY_LITERAL_NODE_CLASS
        ):
            self._syntax_error("function call syntax is name{arguments}", function_name.meta_data)
        pieces, consumed = self._braced_items(line, allow_empty=True)
        arguments = []
        labels = []
        seen = set()
        named = False
        for piece in pieces:
            if (
                len(piece) >= 2
                and piece[0].type_enum_id == self.T_IDENT_ENUM_VAL
                and piece[1].type_enum_id == self.T_ASSIGN_ENUM_VAL
            ):
                label = piece[0].value
                if label in seen:
                    self._syntax_error(f"duplicate named argument '{label}'", piece[0])
                seen.add(label)
                named = True
                expression = piece[2:]
            else:
                if named:
                    self._syntax_error(
                        "positional arguments must precede named arguments", piece[0]
                    )
                label = None
                expression = piece
            arguments.append(self.shunting_yard_algo(expression))
            labels.append(label)
        return self.CALL_NODE_CLASS(
            name=function_name,
            args=arguments,
            meta_data=function_name.meta_data,
            keyword_names=tuple(labels) if named else (),
        ), consumed

    def handle_return(self, line_idx):
        line = self.post_split[line_idx]
        return_token = line[0]
        if len(line) <= 1:
            raise ParserError(
                self.file,
                "Return statement syntax is [return][expression]",
                return_token.line,
                return_token.column_start,
                return_token.column_end,
            )

        expected_expression = line[1:]

        expr_node = self.shunting_yard_algo(expected_expression)

        return_node = self.RETURN_NODE_CLASS(meta_data=return_token, expression=expr_node)

        self.post_SYA.append(return_node)

    def _validate_assignment_target(self, target, token):
        pending = [target]
        while pending:
            current = pending.pop()
            if type(current) not in self.VALID_LEFT_HANDS:
                self._syntax_error("invalid assignment target", token)
            if type(current) is self.ARRAY_LITERAL_NODE_CLASS:
                pending.extend(item.root_expr for item in current.elements)

    def handle_assignments(self, line, assignment_idx):
        VALID_LEFT_HANDS = self.VALID_LEFT_HANDS
        assignment_op_token = line[assignment_idx]
        left_hand = line[:assignment_idx]

        if not left_hand or assignment_idx == len(line) - 1:
            raise ParserError(
                self.file,
                "assignment requires a target and a value",
                assignment_op_token.line,
                assignment_op_token.column_start,
                assignment_op_token.column_end,
            )

        left_hand_node = self.shunting_yard_algo(left_hand).root_expr

        if type(left_hand_node) not in VALID_LEFT_HANDS:
            raise ParserError(
                self.file,
                "assignment statement syntax is [identifier][=][expression]",
                assignment_op_token.line,
                assignment_op_token.column_start,
                assignment_op_token.column_end,
            )

        self._validate_assignment_target(left_hand_node, assignment_op_token)

        expected_expression = line[assignment_idx + 1 :]
        expr_node = self.shunting_yard_algo(expected_expression)

        assignment_node = self.ASSIGNMENT_NODE_CLASS(
            left_hand=left_hand_node,
            op=assignment_op_token.type_enum_id,
            meta_data=assignment_op_token,
            right_hand=expr_node,
        )

        self.post_SYA.append(assignment_node)

    def handle_index(self, base, line):
        INDEX_NODE_CLASS = self.INDEX_NODE_CLASS
        T_RBRACKET_ENUM_VAL = self.T_RBRACKET_ENUM_VAL
        T_LBRACKET_ENUM_VAL = self.T_LBRACKET_ENUM_VAL
        # this must be updated any time a new non-indexable literal option is added to the lang

        if type(base) in self.NOT_INDEXABLE:
            raise ParserError(
                self.file,
                f"Can't index into {base}",
                base.meta_data.line,
                base.meta_data.column_start,
                base.meta_data.column_end,
            )

        left_bracket = line[0]
        depth = 0
        # it's very important to make sure that we're matching the correct depth
        for tok_idx, tok in enumerate(line):
            tok_type_id = tok.type_enum_id
            if tok_type_id == T_RBRACKET_ENUM_VAL:
                depth -= 1
                if depth == 0:
                    expected_expression = line[1:tok_idx]
                    evaluated_expression = self.shunting_yard_algo(expected_expression)
                    if type(base) is not INDEX_NODE_CLASS:
                        return INDEX_NODE_CLASS(
                            base=base, index=[evaluated_expression], meta_data=left_bracket
                        ), tok_idx
                    else:
                        base.index.append(evaluated_expression)
                        return base, tok_idx
            elif tok_type_id == T_LBRACKET_ENUM_VAL:
                depth += 1
        raise ParserError(
            self.file,
            "Mismatched brackets",
            base.meta_data.line,
            base.meta_data.column_start,
            base.meta_data.column_end,
        )

    # if you pass an array into the SYA it will be wrapped in a expression node,
    # but that is only
    # because its the root expression. all an expression node
    # is in this lanaguge is the root of whatever is passed into
    # the SYA, which is why its attribute is root_expr
    def handle_array_literals(self, line):
        ARRAY_LITERAL_NODE_CLASS = self.ARRAY_LITERAL_NODE_CLASS
        DEPTH_CREATORS = self.DEPTH_CREATORS
        DEPTH_ENDERS = self.DEPTH_ENDERS
        T_COMMA_ENUM_VAL = self.T_COMMA_ENUM_VAL
        elements = []
        current = []
        depth = 0
        tok_idx = 1
        creators = []
        while tok_idx < len(line):
            tok = line[tok_idx]
            tok_type_id = tok.type_enum_id

            # ── open bracket ────────────────────────────────────────────────
            if tok_type_id in DEPTH_CREATORS:
                depth += 1
                current.append(tok)
                creators.append(tok)

            # ── close bracket ───────────────────────────────────────────────
            elif tok_type_id in DEPTH_ENDERS:
                if depth == 0:
                    if tok_type_id != DEPTH_CREATORS[line[0].type_enum_id]:
                        raise ParserError(
                            self.file,
                            "mismatched brackets",
                            tok.line,
                            tok.column_start,
                            tok.column_end,
                        )
                    if current:
                        elements.append(self.shunting_yard_algo(current))
                    return ARRAY_LITERAL_NODE_CLASS(elements, meta_data=line[0]), tok_idx
                if not creators or tok_type_id != DEPTH_CREATORS[creators[-1].type_enum_id]:
                    raise ParserError(
                        self.file, "mismatched brackets", tok.line, tok.column_start, tok.column_end
                    )
                depth -= 1
                current.append(tok)
                creators.pop()

            # ── comma that splits *top-level* elements ──────────────────────
            elif tok_type_id == T_COMMA_ENUM_VAL and depth == 0:
                if current:
                    elements.append(self.shunting_yard_algo(current))
                current = []
            # ── anything else (ident, number, +, etc.) ──────────────────────
            else:
                current.append(tok)

            tok_idx += 1

        raise ParserError(
            self.file,
            f"Unterminated {creators[0].value if creators else line[0].value}",
            line[0].line,
            line[0].column_start,
            line[0].column_end,
        )

    # this is our expression handler
    # whenever we expect an expression in a different handler
    # we will pass the expected piece of our list of Lexemes
    # to this algo, which will either return a valid expression node
    # , or raise an error because the list wasn't a valid expression
    def shunting_yard_algo(self, line):
        self.expression_depth += 1
        try:
            if self.expression_depth > self.MAX_EXPRESSION_DEPTH:
                token = line[0] if line else self.tokens[-1]
                raise ParserError(
                    self.file,
                    f"expression nesting exceeds the limit of {self.MAX_EXPRESSION_DEPTH}",
                    token.line,
                    token.column_start,
                    token.column_end,
                )
            span = line if isinstance(line, TokenSpan) else TokenSpan(line)
            return self._shunting_yard_algo(span)
        except ParserError as error:
            if not error.text:
                error.text = self.file
            raise
        except RecursionError as error:
            token = line[0] if line else self.tokens[-1]
            raise ParserError(
                self.file,
                "expression nesting is too deep",
                token.line,
                token.column_start,
                token.column_end,
            ) from error
        finally:
            self.expression_depth -= 1

    def _shunting_yard_algo(self, line):
        if not line:
            anchor = self.tokens[-1] if self.tokens else None
            raise ParserError(
                self.file,
                "expected an expression",
                anchor.line if anchor else 1,
                anchor.column_start if anchor else 1,
                anchor.column_end if anchor else 1,
            )
        output = []
        op_stack = []
        expect_operand = True

        # since we want to treat any field access in the same vein
        # as a literal, it must take priority over every single other
        # non-literal, so we create this collapser function and inject it
        # into the caller for indexing and function literals to ensure this
        def _collapse_field_ops():
            # op_stack item = tuple(token, token_type)
            T_DOT_ENUM_VAL = self.T_DOT_ENUM_VAL
            while op_stack and op_stack[-1][1] == T_DOT_ENUM_VAL:
                apply_operator()

        def apply_operator():
            op_tok, op_tok_type_id = op_stack.pop()
            arity = 1 if self.IS_UNARY[op_tok_type_id] else 2
            if len(output) < arity:
                raise ParserError(
                    self.file,
                    "operator is missing an operand",
                    op_tok.line,
                    op_tok.column_start,
                    op_tok.column_end,
                )

            # unary
            # we probably want to make this and most other things in this
            # parser called from a first-class dict
            if self.IS_UNARY[op_tok_type_id]:
                operand = output.pop()
                output.append(
                    self.UNARY_OP_NODE_CLASS(op=op_tok_type_id, meta_data=op_tok, operand=operand)
                )
            elif op_tok_type_id == self.T_DOT_ENUM_VAL:
                right = output.pop()
                left = output.pop()
                if type(right) is not self.IDENTIFIER_NODE_CLASS:
                    raise ParserError(
                        self.file,
                        "member access must be an identifier",
                        op_tok.line,
                        op_tok.column_start,
                        op_tok.column_end,
                    )
                if type(left) is self.FIELD_ACCESS_NODE_CLASS:
                    left.field.append(right.value)
                    output.append(left)
                else:
                    output.append(
                        self.FIELD_ACCESS_NODE_CLASS(
                            base=left, field=[right.value], meta_data=op_tok
                        )
                    )
            else:
                # binary
                right = output.pop()
                left = output.pop()
                output.append(
                    self.BIN_OP_NODE_CLASS(
                        left=left, op=op_tok_type_id, meta_data=op_tok, right=right
                    )
                )

        # the while loop is really important; it can't be replaced
        # with a for loop because we want a simple way to skip entire portions of
        # code if we encounter a string, array, etc. this is called tight loop optimization
        tok_idx = 0
        line_len = len(line)
        while tok_idx < line_len:
            tok = line[tok_idx]
            tok_type_id = tok.type_enum_id

            if expect_operand and self.IS_BIN2UN[tok_type_id]:
                tok_type_id = self.BINARY_TO_UNARY_OP[tok_type_id]

            if expect_operand and tok_type_id == self.T_FN_ENUM_VAL:
                function, consumed = self.handle_anonymous_function(line[tok_idx:])
                output.append(function)
                tok_idx += consumed
                expect_operand = False
                continue

            if self.IS_ASSIGN[tok_type_id]:
                raise ParserError(
                    self.file,
                    "assignment is only allowed as a statement",
                    tok.line,
                    tok.column_start,
                    tok.column_end,
                )

            # ----------------------------------------------------------------ERROR CHECKING START

            # define the can_follow groups with all expression-level syntax
            # and so if a token isn't in these two, it isn't a token meant for expressions
            if not self.CAN_OPND[tok_type_id] and not self.CAN_OPR[tok_type_id]:
                raise ParserError(
                    self.file,
                    "token not allowed in expressions",
                    tok.line,
                    tok.column_start,
                    tok.column_end,
                )

            # we should naturally never come across an R bracket
            # because that means we didn't come across
            # a LBRACKET first, and that merits an immediate error
            elif tok_type_id in (self.T_RBRACKET_ENUM_VAL, self.T_RBRACE_ENUM_VAL):
                raise ParserError(
                    self.file, "Mismatched grouping", tok.line, tok.column_start, tok.column_end
                )

            elif expect_operand:
                if not self.CAN_OPR[tok_type_id]:
                    raise ParserError(
                        self.file,
                        "Token not allowed to follow to follow operator or start expression",
                        tok.line,
                        tok.column_start,
                        tok.column_end,
                    )
                    # these token types are the operands mentioned above
                    # that dont merit a state transition
                if (
                    tok_type_id not in (self.T_LBRACKET_ENUM_VAL, self.T_LPAREN_ENUM_VAL)
                    and not self.IS_UNARY[tok_type_id]
                ):
                    expect_operand = False

            else:
                if not self.CAN_OPND[tok_type_id]:
                    raise ParserError(
                        self.file,
                        "Token not allowed to follow operand",
                        tok.line,
                        tok.column_start,
                        tok.column_end,
                    )
                if tok_type_id not in (self.T_LBRACKET_ENUM_VAL, self.T_RPAREN_ENUM_VAL):
                    expect_operand = True

            # ----------------------------------------------------------ERROR CHECKING FINISHED

            # A) Literals & identifiers → output
            if self.IS_LITERAL[tok_type_id]:
                output.append(self.LITERAL_MAP[tok_type_id](tok))

            elif tok_type_id == self.T_IDENT_ENUM_VAL:
                output.append(self.IDENTIFIER_NODE_CLASS(value=tok.value, meta_data=tok))

            # handling array literal in seperate function
            elif tok_type_id == self.T_LBRACKET_ENUM_VAL:
                # if the bracket is following an operator and thus
                # expecting an operand we must treat the brackets as an array literal
                if expect_operand:
                    expected_array_literal = line[tok_idx:]
                    array_literal, consumed = self.handle_array_literals(expected_array_literal)
                    output.append(array_literal)
                    tok_idx += consumed
                # if we are following an operand, that means we just parsed a identifier, integer,
                # string, or maybe even an unary node which means the only way for this
                # line to be valid is to parse the brackets as an index node. of course
                # if the previous operand turns out to be a integer or unary node, which cant
                # be indexed we'll throw an error, but the general rule still stands: if
                # its an array following an operand, it has to be an index
                else:
                    _collapse_field_ops()
                    base = output.pop()
                    idx_node, consumed = self.handle_index(base, line[tok_idx:])
                    output.append(idx_node)
                    tok_idx += consumed
                expect_operand = False

            elif tok_type_id == self.T_LBRACE_ENUM_VAL:
                _collapse_field_ops()
                function_name = output.pop()
                call_node, consumed = self.handle_function_call(line[tok_idx:], function_name)
                output.append(call_node)
                tok_idx += consumed
                expect_operand = False

            # C) Any operator
            elif tok_type_id in self.PRECEDENCE:
                PRECEDENCE = self.PRECEDENCE
                p1 = PRECEDENCE[tok_type_id]
                assoc = self.ASSOCIATIVITY[tok_type_id]
                # op_stack item = tuple(token, token_type_id)
                while op_stack and op_stack[-1][1] in PRECEDENCE:
                    top, top_type_id = op_stack[-1]
                    p2 = PRECEDENCE[top_type_id]
                    if (assoc == "left" and p1 <= p2) or (assoc == "right" and p1 < p2):
                        apply_operator()
                    else:
                        break
                op_stack.append((tok, tok_type_id))

            # D) Left grouping
            elif tok_type_id == self.T_LPAREN_ENUM_VAL:
                op_stack.append((tok, tok_type_id))

            # F) right paren
            elif tok_type_id == self.T_RPAREN_ENUM_VAL:
                # op_stack item = tuple(token, token_type)
                while op_stack and op_stack[-1][1] != self.T_LPAREN_ENUM_VAL:
                    apply_operator()
                if not op_stack:
                    raise ParserError(
                        self.file, "Mismatched grouping", tok.line, tok.column_start, tok.column_end
                    )
                op_stack.pop()  # discard '('

            tok_idx += 1

        if expect_operand:
            last = line[-1]
            raise ParserError(
                self.file,
                "expected an operand after this token",
                last.line,
                last.column_start,
                last.column_end,
            )
        while op_stack:
            top, top_type_id = op_stack[-1]
            if top_type_id in (self.T_LPAREN_ENUM_VAL, self.T_RPAREN_ENUM_VAL):
                raise ParserError(
                    self.file, "Mismatched grouping", top.line, top.column_start, top.column_end
                )
            if not output:
                raise ParserError(
                    self.file,
                    "operator has no operand to bind to",
                    top.line,
                    top.column_start,
                    top.column_end,
                )
            apply_operator()

        if len(output) != 1:
            last = line[-1]
            raise ParserError(
                self.file,
                "expected exactly one expression",
                last.line,
                last.column_start,
                last.column_end,
            )
        root = output.pop()
        return self.EXPRESSION_NODE_CLASS(root_expr=root)
