# after this we are guaranteed to have every expression converted into an AST
# and every line construct such as if, elif, fn, converted into its respective
# node. line-wise, the program is syntactically valid

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


class ExpressionParser:
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
        T_INT_ENUM_VAL: lambda tok: (INTEGER_LITERAL_NODE_CLASS(int(tok.value), tok)),
        T_FLOAT_ENUM_VAL: lambda tok: FLOAT_LITERAL_NODE_CLASS(float(tok.value), tok),
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

    # we're going to split the tokens into seperate lines,
    # where each line will be transformed into a singular node
    def split(self):
        T_SEMICOLON_ENUM_VAL = self.T_SEMICOLON_ENUM_VAL
        if getattr(self.__class__, "IS_ASSIGN", None) is None:
            self.__class__._init_type_tables()
        past = -1
        for tok in self.tokens:
            tok_enum_val = tok.type_enum_id

            tok_line = tok.line
            if tok_enum_val == T_SEMICOLON_ENUM_VAL:
                if self.post_split and self.post_split[-1]:  # don’t keep double blanks
                    self.post_split.append([])
                continue

            if tok_line != past:
                self.post_split.append([])
                past = tok_line
            self.post_split[-1].append(tok)
        # for cases such as i = 5; \n
        if self.post_split and not self.post_split[-1]:
            self.post_split.pop()

        return self.post_split

    # most constructs in this lang follow wildy different layouts (sometimes very unique)
    # and so to avoid creating a single parsing algo that can handle all of these different
    # constructs, it's easier to handle each singular construct different, and allow
    # them to interweave with eachother to create a legible Node
    def loading_into_algos(self):
        T_IF_ENUM_VAL = self.T_IF_ENUM_VAL
        T_ELIF_ENUM_VAL = self.T_ELIF_ENUM_VAL
        T_ELSE_ENUM_VAL = self.T_ELSE_ENUM_VAL
        T_FOR_ENUM_VAL = self.T_FOR_ENUM_VAL
        T_WHILE_ENUM_VAL = self.T_WHILE_ENUM_VAL
        T_BREAK_ENUM_VAL = self.T_BREAK_ENUM_VAL
        T_CONTINUE_ENUM_VAL = self.T_CONTINUE_ENUM_VAL
        T_RETURN_ENUM_VAL = self.T_RETURN_ENUM_VAL
        T_END_ENUM_VAL = self.T_END_ENUM_VAL
        T_FN_ENUM_VAL = self.T_FN_ENUM_VAL
        T_DATA_ENUM_VAL = self.T_DATA_ENUM_VAL
        for line_idx, line in enumerate(self.post_split):
            self.illegal_assignment = 0
            if not line:
                continue

            first = line[0]
            first_type_id = first.type_enum_id

            # keyword constructs must start the line, so check only first token
            if first_type_id in (T_IF_ENUM_VAL, T_ELIF_ENUM_VAL, T_ELSE_ENUM_VAL):
                self.handle_if_else_condition(line_idx)
                continue
            if first_type_id == T_FOR_ENUM_VAL:
                self.handle_for_loop(line_idx)
                continue
            if first_type_id == T_WHILE_ENUM_VAL:
                self.handle_while_loop(line_idx)
                continue
            if first_type_id in (T_BREAK_ENUM_VAL, T_CONTINUE_ENUM_VAL, T_END_ENUM_VAL):
                self.handle_single_tokens(line_idx)
                continue
            if first_type_id == T_FN_ENUM_VAL:
                self.handle_function_def(line_idx)
                continue
            if first_type_id == T_DATA_ENUM_VAL:
                self.handle_dataclass_def(line_idx)
                continue
            if first_type_id == T_RETURN_ENUM_VAL:
                self.handle_return(line_idx)
                continue

            # otherwise it's an expression/assignment line
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
        if if_token_id == T_ELSE_ENUM_VAL:
            else_node = ELSE_NODE_CLASS(meta_data=if_token)
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
                IF_NODE_CLASS(condition=expr_node, meta_data=if_token)
                if if_token_id == T_IF_ENUM_VAL
                else ELIF_NODE_CLASS(condition=expr_node, meta_data=if_token)
            )

            self.post_SYA.append(if_node)

    def handle_for_loop(self, line_idx):
        line = self.post_split[line_idx]

        for_token = line[0]
        if len(line) < 3:
            raise ParserError(
                self.file,
                "for loop syntax is '[for][some identifier][some expression]'",
                for_token.line,
                for_token.column_start,
                for_token.column_end,
            )

        variable_token = line[1]
        if variable_token.type_enum_id != T_IDENT_ENUM_VAL:
            raise ParserError(
                self.file,
                "for loop syntax is '[for][some identifier][some expression]'",
                variable_token.line,
                variable_token.column_start,
                variable_token.column_end,
            )

        expected_expression = line[2:]

        variable_node = IDENTIFIER_NODE_CLASS(value=variable_token.value, meta_data=variable_token)
        expr_node = self.shunting_yard_algo(expected_expression)

        for_node = FOR_NODE_CLASS(variable=variable_node, bound=expr_node, meta_data=variable_token)

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

        while_node = WHILE_NODE_CLASS(condition=expr_node, meta_data=while_token)

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
        single_token_to_class = {
            T_END_ENUM_VAL: END_NODE_CLASS,
            T_BREAK_ENUM_VAL: BREAK_NODE_CLASS,
            T_CONTINUE_ENUM_VAL: CONTINUE_NODE_CLASS,
        }
        single_node = single_token_to_class[single_token.type_enum_id]

        single_node_class = single_node(single_token)

        self.post_SYA.append(single_node_class)

    def handle_function_def(self, line_idx):
        line = self.post_split[line_idx]

        single_token = line[0]
        if len(line) != 3:
            raise ParserError(
                self.file,
                "function declaration syntax is [fn][identifier][identifier]",
                single_token.line,
                single_token.column_start,
                single_token.column_end,
            )

        expected_func_name = line[1]
        expected_args_name = line[2]

        if (
            # not worth localizing
            expected_args_name.type_enum_id != T_IDENT_ENUM_VAL
            or expected_func_name.type_enum_id != T_IDENT_ENUM_VAL
        ):
            raise ParserError(
                self.file,
                "function declaration syntax is [fn][identifier][identifier]",
                single_token.line,
                single_token.column_start,
                single_token.column_end,
            )

        function_node = FUNCTION_NODE_CLASS(
            name=expected_func_name.value,
            arg_list_name=expected_args_name.value,
            meta_data=single_token,
        )
        self.post_SYA.append(function_node)

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
        if dataclass_name.type_enum_id != T_IDENT_ENUM_VAL:
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
        if type(list_of_field_names.root_expr) is not ARRAY_LITERAL_NODE_CLASS or (
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
        dataclass_node = DATA_CLASS_NODE_CLASS(
            dataclass_name.value, list_of_field_names_raw_values, data_keyword_token
        )
        self.post_SYA.append(dataclass_node)

    def handle_function_call(self, line, function_name):
        CALL_NODE_CLASS = self.CALL_NODE_CLASS
        DEPTH_ENDERS = self.DEPTH_ENDERS
        DEPTH_CREATORS = self.DEPTH_CREATORS
        T_COMMA_ENUM_VAL = self.T_COMMA_ENUM_VAL
        elements = []
        current = []
        depth = 0
        tok_idx = 1
        creators = []

        if type(function_name) in self.LITERAL_MAP or type(function_name) in (
            ARRAY_LITERAL_NODE_CLASS,
        ):
            raise ParserError(
                self.file,
                "function call syntax is [function name][args]",
                function_name.meta_data.line,
                function_name.meta_data.column_start,
                function_name.meta_data.column_end,
            )
        while tok_idx < len(line):
            tok = line[tok_idx]
            tok_type_id = tok.type_enum_id

            if tok_type_id in DEPTH_CREATORS:
                # entering one more level of nested braces
                depth += 1
                current.append(tok)
                creators.append(tok)

            elif tok_type_id in DEPTH_ENDERS:
                if depth == 0:
                    if current:
                        elements.append(self.shunting_yard_algo(current))

                    return CALL_NODE_CLASS(
                        name=function_name, args=elements, meta_data=function_name.meta_data
                    ), tok_idx

                if not creators or tok_type_id != DEPTH_CREATORS[creators[-1].type_enum_id]:
                    raise ParserError(
                        self.file, "mismatched brackets", tok.line, tok.column_start, tok.column_end
                    )
                depth -= 1
                current.append(tok)
                creators.pop()

            elif tok_type_id == T_COMMA_ENUM_VAL and depth == 0:
                if current:
                    elements.append(self.shunting_yard_algo(current))
                current = []

            else:
                current.append(tok)

            tok_idx += 1
        # if creators dosent exist and we reach this point it means the
        # first bracket which we dont track in creators wasn't closed
        raise ParserError(
            self.file,
            f"Unterminated {creators[0].value if creators else line[0].value}",
            line[0].line,
            line[0].column_start,
            line[0].column_end,
        )

    def handle_return(self, line_idx):
        RETURN_NODE_CLASS = self.RETURN_NODE_CLASS
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

        return_node = RETURN_NODE_CLASS(meta_data=return_token, expression=expr_node)

        self.post_SYA.append(return_node)

    def handle_assignments(self, line, assignment_idx):
        valid_left_hands = (
            INDEX_NODE_CLASS,
            IDENTIFIER_NODE_CLASS,
            ARRAY_LITERAL_NODE_CLASS,
            FIELD_ACCESS_NODE_CLASS,
        )

        assignment_op_token = line[assignment_idx]
        left_hand = line[:assignment_idx]

        left_hand_node = self.shunting_yard_algo(left_hand).root_expr

        if type(left_hand_node) not in valid_left_hands:
            raise ParserError(
                self.file,
                "assignment statement syntax is [identifier][=][expression]",
                assignment_op_token.line,
                assignment_op_token.column_start,
                assignment_op_token.column_end,
            )

        if type(left_hand_node) is ARRAY_LITERAL_NODE_CLASS:
            for i in left_hand_node.elements:
                if type(i.root_expr) not in valid_left_hands:
                    raise ParserError(
                        self.file,
                        f"{type(i.root_expr)} multi-initalization syntax is"
                        "[list of identifiers][=][list of expressions]",
                        assignment_op_token.line,
                        assignment_op_token.column_start,
                        assignment_op_token.column_end,
                    )

        expected_expression = line[assignment_idx + 1 :]
        expr_node = self.shunting_yard_algo(expected_expression)

        self.illegal_assignment = 1

        assignment_node = ASSIGNMENT_NODE_CLASS(
            left_hand=left_hand_node,
            op=assignment_op_token.type_enum_id,
            meta_data=assignment_op_token,
            right_hand=expr_node,
        )

        self.post_SYA.append(assignment_node)

        self.illegal_assignment = 2

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
        IDENTIFIER_NODE_CLASS = self.IDENTIFIER_NODE_CLASS

        IS_ASSIGN = self.IS_ASSIGN
        IS_BIN2UN = self.IS_BIN2UN
        CAN_OPND = self.CAN_OPND
        CAN_OPR = self.CAN_OPR
        IS_UNARY = self.IS_UNARY
        IS_LITERAL = self.IS_LITERAL

        ASSOCIATIVITY = self.ASSOCIATIVITY
        BINARY_TO_UNARY_OP = self.BINARY_TO_UNARY_OP
        PRECEDENCE = self.PRECEDENCE
        LITERAL_MAP = self.LITERAL_MAP

        T_IDENT_ENUM_VAL = self.T_IDENT_ENUM_VAL
        T_DOT_ENUM_VAL = self.T_DOT_ENUM_VAL
        T_RBRACKET_ENUM_VAL = self.T_RBRACKET_ENUM_VAL
        T_RBRACE_ENUM_VAL = self.T_RBRACE_ENUM_VAL
        T_LBRACKET_ENUM_VAL = self.T_LBRACKET_ENUM_VAL
        T_LPAREN_ENUM_VAL = self.T_LPAREN_ENUM_VAL
        T_RPAREN_ENUM_VAL = self.T_RPAREN_ENUM_VAL
        T_LBRACE_ENUM_VAL = self.T_LBRACE_ENUM_VAL

        output = []
        op_stack = []
        expect_operand = True

        # since we want to treat any field access in the same vein
        # as a literal, it must take priority over every single other
        # non-literal, so we create this collapser function and inject it
        # into the caller for indexing and function literals to ensure this
        def _collapse_field_ops():
            # op_stack item = tuple(token, token_type)
            while op_stack and op_stack[-1][1] == T_DOT_ENUM_VAL:
                apply_operator()

        def apply_operator():
            FIELD_ACCESS_NODE_CLASS = self.FIELD_ACCESS_NODE_CLASS
            op_tok, op_tok_type_id = op_stack.pop()
            is_unary = IS_UNARY[op_tok_type_id]
            # unary
            # we probably want to make this and most other things in this
            # parser called from a first-class dict
            if is_unary:
                operand = output.pop()
                output.append(
                    UNARY_OP_NODE_CLASS(op=op_tok_type_id, meta_data=op_tok, operand=operand)
                )
            elif op_tok_type_id == T_DOT_ENUM_VAL:
                right = output.pop()
                left = output.pop()
                if type(right) is not IDENTIFIER_NODE_CLASS:
                    raise ParserError(
                        self.file,
                        "member access must be an identifier",
                        op_tok.line,
                        op_tok.column_start,
                        op_tok.column_end,
                    )
                if type(left) is FIELD_ACCESS_NODE_CLASS:
                    left.field.append(right.value)
                    output.append(left)
                else:
                    output.append(
                        FIELD_ACCESS_NODE_CLASS(base=left, field=[right.value], meta_data=op_tok)
                    )
            else:
                # binary
                right = output.pop()
                left = output.pop()
                output.append(
                    BIN_OP_NODE_CLASS(left=left, op=op_tok_type_id, meta_data=op_tok, right=right)
                )

        # the while loop is really important; it can't be replaced
        # with a for loop because we want a simple way to skip entire portions of
        # code if we encounter a string, array, etc. this is called tight loop optimization
        tok_idx = 0
        line_len = len(line)
        while tok_idx < line_len:
            tok = line[tok_idx]
            tok_type_id = tok.type_enum_id

            if expect_operand and IS_BIN2UN[tok_type_id]:
                tok_type_id = BINARY_TO_UNARY_OP[tok_type_id]

            # ------------------------------- BOOL FLAGS
            tok_type_in_ASSIGNMENT = IS_ASSIGN[tok_type_id]
            tok_type_in_CAN_FOLLOW_OPERAND = CAN_OPND[tok_type_id]
            tok_type_in_CAN_FOLLOW_OPERATOR = CAN_OPR[tok_type_id]
            tok_type_in_UNARY_OPS = IS_UNARY[tok_type_id]
            tok_type_in_LITERAL_MAP = IS_LITERAL[tok_type_id]

            # ------------------------------- BOOL FLAGS

            if tok_type_in_ASSIGNMENT:
                if self.illegal_assignment:
                    raise ParserError(
                        self.file, "illegal assignment", tok.line, tok.column_start, tok.column_end
                    )

                self.handle_assignments(line, tok_idx)
                tok_idx = len(line)
                continue

            # ----------------------------------------------------------------ERROR CHECKING START

            # define the can_follow groups with all expression-level syntax
            # and so if a token isn't in these two, it isn't a token meant for expressions
            if not tok_type_in_CAN_FOLLOW_OPERAND and not tok_type_in_CAN_FOLLOW_OPERATOR:
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
            elif tok_type_id in (T_RBRACKET_ENUM_VAL, T_RBRACE_ENUM_VAL):
                raise ParserError(
                    self.file, "Mismatched grouping", tok.line, tok.column_start, tok.column_end
                )

            elif expect_operand:
                if not tok_type_in_CAN_FOLLOW_OPERATOR:
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
                    tok_type_id not in (T_LBRACKET_ENUM_VAL, T_LPAREN_ENUM_VAL)
                    and not tok_type_in_UNARY_OPS
                ):
                    expect_operand = False

            else:
                if not tok_type_in_CAN_FOLLOW_OPERAND:
                    raise ParserError(
                        self.file,
                        "Token not allowed to follow operand",
                        tok.line,
                        tok.column_start,
                        tok.column_end,
                    )
                if tok_type_id not in (T_LBRACKET_ENUM_VAL, T_RPAREN_ENUM_VAL):
                    expect_operand = True

            # ----------------------------------------------------------ERROR CHECKING FINISHED

            # A) Literals & identifiers → output
            if tok_type_in_LITERAL_MAP:
                output.append(LITERAL_MAP[tok_type_id](tok))

            elif tok_type_id == T_IDENT_ENUM_VAL:
                output.append(IDENTIFIER_NODE_CLASS(value=tok.value, meta_data=tok))

            # handling array literal in seperate function
            elif tok_type_id == T_LBRACKET_ENUM_VAL:
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

            elif tok_type_id == T_LBRACE_ENUM_VAL:
                _collapse_field_ops()
                function_name = output.pop()
                call_node, consumed = self.handle_function_call(line[tok_idx:], function_name)
                output.append(call_node)
                tok_idx += consumed
                expect_operand = False

            # C) Any operator
            elif tok_type_id in PRECEDENCE:
                p1 = PRECEDENCE[tok_type_id]
                assoc = ASSOCIATIVITY[tok_type_id]
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
            elif tok_type_id == T_LPAREN_ENUM_VAL:
                op_stack.append((tok, tok_type_id))

            # F) right paren
            elif tok_type_id == T_RPAREN_ENUM_VAL:
                # op_stack item = tuple(token, token_type)
                while op_stack and op_stack[-1][1] != T_LPAREN_ENUM_VAL:
                    apply_operator()
                if not op_stack:
                    raise ParserError(
                        self.file, "Mismatched grouping", tok.line, tok.column_start, tok.column_end
                    )
                op_stack.pop()  # discard '('

            tok_idx += 1

        if self.illegal_assignment != 2:
            while op_stack:
                top, top_type_id = op_stack[-1]
                if top_type_id in (T_LPAREN_ENUM_VAL, T_RPAREN_ENUM_VAL):
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

            root = output.pop()
            return EXPRESSION_NODE_CLASS(root_expr=root)
