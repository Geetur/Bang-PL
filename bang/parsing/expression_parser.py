# after this we are guaranteed to have every expression converted into an AST
# and every line construct such as if, elif, fn, converted into its respective
# node. line-wise, the program is syntactically valid


from bang.lexing.lexer import Lexer, TokenType
from bang.parsing.parser_nodes import (
    ArrayLiteralNode,
    AssignmentNode,
    BinOpNode,
    BooleanLiteralNode,
    BreakNode,
    CallNode,
    ContinueNode,
    DataClassNode,
    ElifNode,
    ElseNode,
    EndNode,
    ExpressionNode,
    FieldAccessNode,
    FloatLiteralNode,
    ForNode,
    FunctionNode,
    IdentifierNode,
    IFNode,
    IndexNode,
    IntegerLiteralNode,
    NoneLiteralNode,
    ReturnNode,
    StringLiteralNode,
    UnaryOPNode,
    WhileNode,
)


class ParserError(Exception):
    def __init__(self, file, msg, row, start, end):
        self.file = file
        self.msg = msg
        self.row = row
        self.start = start
        self.end = end

        super().__init__(self._format())

    def _get_real_error_line(self):
        with open(self.file) as f:
            for row_idx, row in enumerate(f):
                if row_idx == self.row:
                    return row

    def _format(self):
        error_line = self._get_real_error_line()
        crt_length = self.end - self.start if self.end - self.start != 0 else 1
        pointers = " " * self.start + "^" * crt_length
        return (
            f"[ParserError] Line {self.row + 1}, Column {self.start}-{self.end}:\n"
            f"{error_line.rstrip()}\n"
            f"{pointers}\n"
            f"{self.msg}"
        )

    def __str__(self) -> str:
        return self._format()

    __repr__ = __str__


class ExpressionParser:
    # 1) Precedence (higher = tighter binding)
    PRECEDENCE = {
        # assignments & compound-assign
        # logical
        TokenType.T_OR: 2,  # ||
        TokenType.T_AND: 3,  # &&
        # equality
        TokenType.T_EQ: 4,  # ==
        TokenType.T_NEQ: 4,  # !=
        TokenType.T_IN: 4,
        # relational
        TokenType.T_LT: 5,  # <
        TokenType.T_LEQ: 5,  # <=
        TokenType.T_GT: 5,  # >
        TokenType.T_GTEQ: 5,  # >=
        # additive
        TokenType.T_PLUS: 6,  # +
        TokenType.T_MINUS: 6,  # -
        # multiplicative
        TokenType.T_ASTERISK: 7,  # *
        TokenType.T_SLASH: 7,  # /
        TokenType.T_DSLASH: 7,  # //
        # exponent
        TokenType.T_EXPO: 8,  # **
        # unary
        TokenType.T_NEGATE: 9,  # !
        TokenType.T_UPLUS: 9,
        TokenType.T_UMINUS: 9,
        TokenType.T_DOT: 10,
    }

    # you can technically handle assignments within the SYA
    # but in the spirit or our parser, anything other than expressions
    # with be thrust into a seperate modular function
    ASSOCIATIVITY = {
        # right-assoc
        **{
            op: "right"
            for op in (
                TokenType.T_UPLUS,
                TokenType.T_UMINUS,
                TokenType.T_EXPO,
                TokenType.T_NEGATE,
            )
        },
        # left-assoc
        **{
            op: "left"
            for op in (
                TokenType.T_OR,
                TokenType.T_AND,
                TokenType.T_EQ,
                TokenType.T_NEQ,
                TokenType.T_LT,
                TokenType.T_LEQ,
                TokenType.T_GT,
                TokenType.T_GTEQ,
                TokenType.T_PLUS,
                TokenType.T_MINUS,
                TokenType.T_ASTERISK,
                TokenType.T_SLASH,
                TokenType.T_DSLASH,
                TokenType.T_IN,
                TokenType.T_DOT,
            )
        },
    }
    ASSIGNMENT = {
        TokenType.T_ASSIGN,
        TokenType.T_PLUS_ASSIGN,
        TokenType.T_MINUS_ASSIGN,
        TokenType.T_SLASH_ASSIGN,
        TokenType.T_ASTERISK_ASSIGN,
    }

    DEPTH_CREATORS = {
        TokenType.T_LBRACKET: TokenType.T_RBRACKET,
        TokenType.T_LBRACE: TokenType.T_RBRACE,
    }

    DEPTH_ENDERS = {TokenType.T_RBRACKET, TokenType.T_RBRACE}

    UNARY_OPS = {
        TokenType.T_UPLUS,
        TokenType.T_UMINUS,
        TokenType.T_NEGATE,
    }

    BINARY_TO_UNARY_OP = {
        TokenType.T_PLUS: TokenType.T_UPLUS,
        TokenType.T_MINUS: TokenType.T_UMINUS,
        TokenType.T_NEGATE: TokenType.T_NEGATE,
    }

    CAN_FOLLOW_OPERATOR = {
        TokenType.T_INT,
        TokenType.T_FLOAT,
        TokenType.T_BOOL,
        TokenType.T_NONE,
        TokenType.T_IDENT,
        TokenType.T_LBRACKET,
        TokenType.T_LPAREN,
        TokenType.T_UMINUS,
        TokenType.T_UPLUS,
        TokenType.T_NEGATE,
        TokenType.T_STRING,
    }

    # can_follow is a really elegant way to handle errors in the shunting yard algorithm
    # we essentially define a two-state transition, and based on our
    # current state we can either allow the next token, or throw an error
    # another important aspect to this transition is that not every operand expects an operator
    # whereas every operator expects an operand and so you can define an additional table
    # or information that defines each operand with a true or false value to determine whether
    # it merits a state transition, but there are so few you can typically just if statement

    CAN_FOLLOW_OPERAND = (set(PRECEDENCE) - UNARY_OPS) | {
        TokenType.T_RPAREN,
        TokenType.T_RBRACKET,
        # this can follow an operand because in the case an array
        # follows an operand it can be an index node
        # if the operand isn't indexable we throw and error in the index handler
        TokenType.T_LBRACKET,
        TokenType.T_LBRACE,
        TokenType.T_RBRACE,
        TokenType.T_DOT,
    }

    # these are literals that can be instantly determined, unlike
    # arrays which must be determined over n tokens
    LITERAL_MAP = {
        TokenType.T_INT: lambda tok: IntegerLiteralNode(int(tok.value), tok),
        TokenType.T_FLOAT: lambda tok: FloatLiteralNode(float(tok.value), tok),
        TokenType.T_BOOL: lambda tok: BooleanLiteralNode(
            (True if tok.value == "true" else False), tok
        ),
        TokenType.T_NONE: lambda tok: NoneLiteralNode(tok.value, tok),
        TokenType.T_STRING: lambda tok: StringLiteralNode(tok.value, tok),
    }

    NOT_INDEXABLE = {IntegerLiteralNode, FloatLiteralNode, NoneLiteralNode, BooleanLiteralNode}

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
            cls.IS_ASSIGN[v] = t in cls.ASSIGNMENT
            cls.IS_BIN2UN[v] = t in cls.BINARY_TO_UNARY_OP
            cls.CAN_OPND[v] = t in cls.CAN_FOLLOW_OPERAND
            cls.CAN_OPR[v] = t in cls.CAN_FOLLOW_OPERATOR
            cls.IS_UNARY[v] = t in cls.UNARY_OPS
            cls.IS_LITERAL[v] = t in cls.LITERAL_MAP

    def __init__(self, tokens, file):
        self.file = file
        self.tokens = tokens
        self.post_split = []
        self.post_SYA = []
        self.illegal_assignment = 0

    # we're going to split the tokens into seperate lines,
    # where each line will be transformed into a singular node
    def split(self):
        if getattr(self.__class__, "IS_ASSIGN", None) is None:
            self.__class__._init_type_tables()
        past = -1
        for tok in self.tokens:
            tok_type = tok.type
            tok_line = tok.line
            if tok_type == TokenType.T_SEMICOLON:
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
        for line_idx, line in enumerate(self.post_split):
            self.illegal_assignment = 0
            for tok_idx, tok in enumerate(line):
                tok_type = tok.type
                tok_value = tok.value
                if tok_value in Lexer.KEYWORDS:
                    if tok_idx != 0:
                        raise ParserError(
                            self.file,
                            f"{tok} keyword must be the first token in a line",
                            tok.line,
                            tok.column_start,
                            tok.column_end,
                        )
                    elif tok_type in (TokenType.T_IF, TokenType.T_ELIF, TokenType.T_ELSE):
                        self.handle_if_else_condition(line_idx)
                        break
                    elif tok_type == TokenType.T_FOR:
                        self.handle_for_loop(line_idx)
                        break
                    elif tok_type == TokenType.T_WHILE:
                        self.handle_while_loop(line_idx)
                        break
                    elif tok_type in (
                        TokenType.T_BREAK,
                        TokenType.T_CONTINUE,
                        TokenType.T_END,
                    ):
                        self.handle_single_tokens(line_idx)
                        break
                    elif tok_type == TokenType.T_FN:
                        self.handle_function_def(line_idx)
                        break
                    elif tok_type == TokenType.T_DATA:
                        self.handle_dataclass_def(line_idx)
                        break
                    elif tok_type == TokenType.T_RETURN:
                        self.handle_return(line_idx)
                        break

                elif tok_idx == len(line) - 1:
                    expected_expr = self.shunting_yard_algo(line)
                    if expected_expr is not None:
                        self.post_SYA.append(expected_expr)
                    break
        return self.post_SYA

    def handle_if_else_condition(self, line_idx):
        line = self.post_split[line_idx]
        if_token = line[0]

        # handling the else keyword seperately for the if and elif
        # since it follows different syntax than the if-elif constructs
        if if_token.type == TokenType.T_ELSE:
            else_node = ElseNode(meta_data=if_token)
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
                IFNode(condition=expr_node, meta_data=if_token)
                if if_token.type == TokenType.T_IF
                else ElifNode(condition=expr_node, meta_data=if_token)
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
        if variable_token.type != TokenType.T_IDENT:
            raise ParserError(
                self.file,
                "for loop syntax is '[for][some identifier][some expression]'",
                variable_token.line,
                variable_token.column_start,
                variable_token.column_end,
            )

        expected_expression = line[2:]

        variable_node = IdentifierNode(value=variable_token.value, meta_data=variable_token)
        expr_node = self.shunting_yard_algo(expected_expression)

        for_node = ForNode(variable=variable_node, bound=expr_node, meta_data=variable_token)

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

        while_node = WhileNode(condition=expr_node, meta_data=while_token)

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
            TokenType.T_END: EndNode,
            TokenType.T_BREAK: BreakNode,
            TokenType.T_CONTINUE: ContinueNode,
        }
        single_node = single_token_to_class[single_token.type]

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
            expected_args_name.type != TokenType.T_IDENT
            or expected_func_name.type != TokenType.T_IDENT
        ):
            raise ParserError(
                self.file,
                "function declaration syntax is [fn][identifier][identifier]",
                single_token.line,
                single_token.column_start,
                single_token.column_end,
            )

        function_node = FunctionNode(
            name=expected_func_name.value,
            arg_list_name=expected_args_name.value,
            meta_data=single_token,
        )
        self.post_SYA.append(function_node)

    def handle_dataclass_def(self, line_idx):
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
        if dataclass_name.type != TokenType.T_IDENT:
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
        if type(list_of_field_names.root_expr) is not ArrayLiteralNode or (
            any(
                type(i.root_expr) is not IdentifierNode
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
        dataclass_node = DataClassNode(
            dataclass_name.value, list_of_field_names_raw_values, data_keyword_token
        )
        self.post_SYA.append(dataclass_node)

    def handle_function_call(self, line, function_name):
        elements = []
        current = []
        depth = 0
        tok_idx = 1
        creators = []

        if type(function_name) in self.LITERAL_MAP or type(function_name) in (ArrayLiteralNode,):
            raise ParserError(
                self.file,
                "function call syntax is [function name][args]",
                function_name.meta_data.line,
                function_name.meta_data.column_start,
                function_name.meta_data.column_end,
            )
        while tok_idx < len(line):
            tok = line[tok_idx]
            tok_type = tok.type

            if tok_type in self.DEPTH_CREATORS:
                # entering one more level of nested braces
                depth += 1
                current.append(tok)
                creators.append(tok)

            elif tok_type in self.DEPTH_ENDERS:
                if depth == 0:
                    if current:
                        elements.append(self.shunting_yard_algo(current))

                    return CallNode(
                        name=function_name, args=elements, meta_data=function_name.meta_data
                    ), tok_idx

                if not creators or tok_type != self.DEPTH_CREATORS[creators[-1].type]:
                    raise ParserError(
                        self.file, "mismatched brackets", tok.line, tok.column_start, tok.column_end
                    )
                depth -= 1
                current.append(tok)
                creators.pop()

            elif tok_type == TokenType.T_COMMA and depth == 0:
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

        return_node = ReturnNode(meta_data=return_token, expression=expr_node)

        self.post_SYA.append(return_node)

    def handle_assignments(self, line, assignment_idx):
        valid_left_hands = {IndexNode, IdentifierNode, ArrayLiteralNode, FieldAccessNode}

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

        if type(left_hand_node) is ArrayLiteralNode:
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

        assignment_node = AssignmentNode(
            left_hand=left_hand_node,
            op=assignment_op_token.type,
            meta_data=assignment_op_token,
            right_hand=expr_node,
        )

        self.post_SYA.append(assignment_node)

        self.illegal_assignment = 2

    def handle_index(self, base, line):
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
            tok_type = tok.type
            if tok_type == TokenType.T_RBRACKET:
                depth -= 1
                if depth == 0:
                    expected_expression = line[1:tok_idx]
                    evaluated_expression = self.shunting_yard_algo(expected_expression)
                    if type(base) is not IndexNode:
                        return IndexNode(
                            base=base, index=[evaluated_expression], meta_data=left_bracket
                        ), tok_idx
                    else:
                        base.index.append(evaluated_expression)
                        return base, tok_idx
            elif tok_type == TokenType.T_LBRACKET:
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
        elements = []
        current = []
        depth = 0
        tok_idx = 1
        creators = []

        while tok_idx < len(line):
            tok = line[tok_idx]
            tok_type = tok.type

            # ── open bracket ────────────────────────────────────────────────
            if tok_type in self.DEPTH_CREATORS:
                depth += 1
                current.append(tok)
                creators.append(tok)

            # ── close bracket ───────────────────────────────────────────────
            elif tok_type in self.DEPTH_ENDERS:
                if depth == 0:
                    if current:
                        elements.append(self.shunting_yard_algo(current))
                    return ArrayLiteralNode(elements, meta_data=line[0]), tok_idx
                if not creators or tok_type != self.DEPTH_CREATORS[creators[-1].type]:
                    raise ParserError(
                        self.file, "mismatched brackets", tok.line, tok.column_start, tok.column_end
                    )
                depth -= 1
                current.append(tok)
                creators.pop()

            # ── comma that splits *top-level* elements ──────────────────────
            elif tok_type == TokenType.T_COMMA and depth == 0:
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
        output = []
        op_stack = []
        expect_operand = True

        cls = self.__class__
        IS_ASSIGN = cls.IS_ASSIGN
        IS_BIN2UN = cls.IS_BIN2UN
        CAN_OPND = cls.CAN_OPND
        CAN_OPR = cls.CAN_OPR
        IS_UNARY = cls.IS_UNARY
        IS_LITERAL = cls.IS_LITERAL

        PRECEDENCE = self.PRECEDENCE

        # since we want to treat any field access in the same vein
        # as a literal, it must take priority over every single other
        # non-literal, so we create this collapser function and inject it
        # into the caller for indexing and function literals to ensure this
        def _collapse_field_ops():
            # op_stack item = tuple(token, token_type)
            while op_stack and op_stack[-1][1] == TokenType.T_DOT:
                apply_operator()

        def apply_operator():
            op_tok, op_tok_type = op_stack.pop()
            is_unary = IS_UNARY[op_tok_type.value]
            # unary
            # we probably want to make this and most other things in this
            # parser called from a first-class dict
            if is_unary:
                operand = output.pop()
                output.append(UnaryOPNode(op=op_tok_type, meta_data=op_tok, operand=operand))
            elif op_tok_type == TokenType.T_DOT:
                right = output.pop()
                left = output.pop()
                if type(right) is not IdentifierNode:
                    raise ParserError(
                        self.file,
                        "member access must be an identifier",
                        op_tok.line,
                        op_tok.column_start,
                        op_tok.column_end,
                    )
                if type(left) is FieldAccessNode:
                    left.field.append(right.value)
                    output.append(left)
                else:
                    output.append(FieldAccessNode(base=left, field=[right.value], meta_data=op_tok))
            else:
                # binary
                right = output.pop()
                left = output.pop()
                output.append(BinOpNode(left=left, op=op_tok_type, meta_data=op_tok, right=right))

        # the while loop is really important; it can't be replaced
        # with a for loop because we want a simple way to skip entire portions of
        # code if we encounter a string, array, etc. this is called tight loop optimization
        tok_idx = 0
        line_len = len(line)
        while tok_idx < line_len:
            tok = line[tok_idx]
            tok_type = tok.type
            v = tok.type_enum_id

            if expect_operand and IS_BIN2UN[v]:
                tok_type = self.BINARY_TO_UNARY_OP[tok_type]
                v = tok_type.value

            # ------------------------------- BOOL FLAGS
            tok_type_in_ASSIGNMENT = IS_ASSIGN[v]
            tok_type_in_CAN_FOLLOW_OPERAND = CAN_OPND[v]
            tok_type_in_CAN_FOLLOW_OPERATOR = CAN_OPR[v]
            tok_type_in_UNARY_OPS = IS_UNARY[v]
            tok_type_in_LITERAL_MAP = IS_LITERAL[v]

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
            elif tok_type in (TokenType.T_RBRACKET, TokenType.T_RBRACE):
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
                    tok_type not in (TokenType.T_LBRACKET, TokenType.T_LPAREN)
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
                if tok_type not in (TokenType.T_LBRACKET, TokenType.T_RPAREN):
                    expect_operand = True

            # ----------------------------------------------------------ERROR CHECKING FINISHED

            # A) Literals & identifiers → output
            if tok_type_in_LITERAL_MAP:
                output.append(self.LITERAL_MAP[tok_type](tok))

            elif tok_type == TokenType.T_IDENT:
                output.append(IdentifierNode(value=tok.value, meta_data=tok))

            # handling array literal in seperate function
            elif tok_type == TokenType.T_LBRACKET:
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

            elif tok_type == TokenType.T_LBRACE:
                _collapse_field_ops()
                function_name = output.pop()
                call_node, consumed = self.handle_function_call(line[tok_idx:], function_name)
                output.append(call_node)
                tok_idx += consumed
                expect_operand = False

            # C) Any operator
            elif tok_type in PRECEDENCE:
                p1 = PRECEDENCE[tok_type]
                assoc = self.ASSOCIATIVITY[tok_type]
                # op_stack item = tuple(token, token_type)
                while op_stack and op_stack[-1][1] in PRECEDENCE:
                    top, top_type = op_stack[-1]
                    p2 = PRECEDENCE[top_type]
                    if (assoc == "left" and p1 <= p2) or (assoc == "right" and p1 < p2):
                        apply_operator()
                    else:
                        break
                op_stack.append((tok, tok_type))

            # D) Left grouping
            elif tok_type == TokenType.T_LPAREN:
                op_stack.append((tok, tok_type))

            # F) right paren
            elif tok_type == TokenType.T_RPAREN:
                # op_stack item = tuple(token, token_type)
                while op_stack and op_stack[-1][1] != TokenType.T_LPAREN:
                    apply_operator()
                if not op_stack:
                    raise ParserError(
                        self.file, "Mismatched grouping", tok.line, tok.column_start, tok.column_end
                    )
                op_stack.pop()  # discard '('

            tok_idx += 1

        if self.illegal_assignment != 2:
            while op_stack:
                top, top_type = op_stack[-1]
                if top_type in (TokenType.T_LPAREN, TokenType.T_RPAREN):
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
            return ExpressionNode(root_expr=root)
