# after this we are guaranteed to have every expression converted into an AST
# and every line construct such as if, elif, fn, converted into its respective
# node. line-wise, the program is syntactically valid

from dataclasses import replace

from bang.lexing.lexer import TokenType, Lexeme, Lexer

from bang.parsing.parser_nodes import (
    IntegerLiteralNode,
    FloatLiteralNode,
    StringLiteralNode,
    IdentifierNode,
    BooleanLiteralNode,
    NoneLiteralNode,
    BinOpNode,
    UnaryOPNode,
    ArrayLiteralNode,
    IndexNode,
    AssignmentNode,
    BlockNode,
    IFNode,
    ElifNode,
    ForNode,
    WhileNode,
    ElseNode,
    FunctionNode,
    CallNode,
    BreakNode,
    ContinueNode,
    EndNode,
    ReturnNode,
    ExpressionNode,
)


class ParserError(Exception):
    def __init__(self, file, msg, row, start, end):
        self.file = file
        self.msg = msg
        self.row = row
        self.start = start
        self.end = end

        super().__init__(self._format())
    
    def _format(self):
        error_line = self.file[self.row]
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
    TokenType.T_OR:              2,   # ||
    TokenType.T_AND:             3,   # &&

    # equality
    TokenType.T_EQ:              4,   # ==
    TokenType.T_NEQ:             4,   # !=

    # relational
    TokenType.T_LT:              5,   # <
    TokenType.T_LEQ:             5,   # <=
    TokenType.T_GT:              5,   # >
    TokenType.T_GTEQ:            5,   # >=

    # additive
    TokenType.T_PLUS:            6,   # +
    TokenType.T_MINUS:           6,   # -

    # multiplicative
    TokenType.T_ASTERISK:        7,   # *
    TokenType.T_SLASH:           7,   # /
    TokenType.T_DSLASH:          7,   # //

    # exponent
    TokenType.T_EXPO:            8,   # **

    # unary
    TokenType.T_NEGATE:          9,   # !
    TokenType.T_UPLUS:           9,
    TokenType.T_UMINUS:          9,

}

    # you can technically handle assignments within the SYA
    # but in the spirit or our parser, anything other than expressions
    # with be thrust into a seperate modular function
    ASSOCIATIVITY = {
    # right-assoc
    **{op: 'right' for op in (
        TokenType.T_UPLUS,
        TokenType.T_UMINUS,
        TokenType.T_EXPO,
        TokenType.T_NEGATE,
    )},
    # left-assoc
    **{op: 'left' for op in (
        TokenType.T_OR, TokenType.T_AND,
        TokenType.T_EQ, TokenType.T_NEQ,
        TokenType.T_LT, TokenType.T_LEQ,
        TokenType.T_GT, TokenType.T_GTEQ,
        TokenType.T_PLUS, TokenType.T_MINUS,
        TokenType.T_ASTERISK, TokenType.T_SLASH, TokenType.T_DSLASH,
    )},
}
    ASSIGNMENT = {
        TokenType.T_ASSIGN, TokenType.T_PLUS_ASSIGN,
        TokenType.T_MINUS_ASSIGN, TokenType.T_SLASH_ASSIGN,
        TokenType.T_ASTERISK_ASSIGN
    }

    DEPTH_CREATORS = {
        TokenType.T_LBRACKET: TokenType.T_RBRACKET, 
        TokenType.T_LBRACE: TokenType.T_RBRACE,
    }

    DEPTH_ENDERS = {
        TokenType.T_RBRACKET, TokenType.T_RBRACE
    }

    def __init__(self, tokens, file):
        self.file = file
        self.tokens = tokens
        self.post_split = []
        self.post_SYA = []
        self.illegal_assignment = 0

        # these are literals that can be instantly determined, unlike
        # strings and arrays which must be determined over n tokens
        self._literal_map = {
            TokenType.T_INT:   lambda tok: IntegerLiteralNode(int(tok.value), tok),
            TokenType.T_FLOAT: lambda tok: FloatLiteralNode(float(tok.value), tok),
            TokenType.T_BOOL: lambda tok: BooleanLiteralNode(
            (True if tok.value == "true" else False), tok),
            TokenType.T_NONE: lambda tok:  NoneLiteralNode(tok.value, tok),
            TokenType.T_STRING: lambda tok: StringLiteralNode(tok.value, tok),
        }


    
    # we're going to split the tokens into seperate lines,
    # where each line will be transformed into a singular node
    # we will then "blockenize" the nodes so that nodes
    # are grouped together under their specific control flows
    def split(self):
        past = -1
        for tok in self.tokens:
            if tok.line != past:
                self.post_split.append([])
                past = tok.line
            self.post_split[-1].append(tok)
        return self.post_split


    def handle_unary_ambiguity(self, line):

        expecting_operand = True

        binary_to_unary_op = {
            TokenType.T_PLUS : TokenType.T_UPLUS,
            TokenType.T_MINUS: TokenType.T_UMINUS,
            TokenType.T_NEGATE: TokenType.T_NEGATE,
        }

        tokens_expecting_operators = {
            TokenType.T_IDENT,
            TokenType.T_INT, TokenType.T_FLOAT, TokenType.T_BOOL, TokenType.T_NONE,
            TokenType.T_STRING,
            TokenType.T_RPAREN, TokenType.T_RBRACKET,
        }

        for tok_idx, tok in enumerate(line):
            if expecting_operand and tok.type in binary_to_unary_op:
                line[tok_idx] = replace(tok, type=binary_to_unary_op[tok.type])
                tok = line[tok_idx]
                
            if tok.type in tokens_expecting_operators:
                expecting_operand = False
            else:
                expecting_operand = (
                    tok.type in self.PRECEDENCE or tok.type in {TokenType.T_LPAREN, TokenType.T_LBRACKET}
                )
        return line
    
    # most constructs in this lang follow wildy different layouts (sometimes very unique)
    # and so to avoid creating a single parsing algo that can handle all of these different
    # constructs, it's easier to handle each singular construct different, and allow
    # them to interweave with eachother to create a legible Node
    def loading_into_algos(self):
        for line_idx, line in enumerate(self.post_split): 
            self.illegal_assignment = 0
            for tok_idx, tok in enumerate(line):
                if tok.value in Lexer.KEYWORDS:
                    if tok_idx != 0:
                        raise ParserError(self.file, f"{tok} keyword must be the first token in a line", tok.line, tok.column_start, tok.column_end)
                    elif tok.type in {TokenType.T_IF, TokenType.T_ELIF, TokenType.T_ELSE}:
                        self.handle_if_else_condition(line_idx)
                        break
                    elif tok.type == TokenType.T_FOR:
                        self.handle_for_loop(line_idx)
                        break
                    elif tok.type == TokenType.T_WHILE:
                        self.handle_while_loop(line_idx)
                        break
                    elif tok.type in {TokenType.T_BREAK, TokenType.T_CONTINUE, 
                                      TokenType.T_END,}:
                        self.handle_single_tokens(line_idx)
                        break
                    elif tok.type == TokenType.T_FN:
                        self.handle_function_def(line_idx)
                        break
                    elif tok.type == TokenType.T_RETURN:
                        self.handle_return(line_idx)
                        break
                
                elif tok_idx == len(line) - 1:
                    expected_expr = self.shunting_yard_algo(line)
                    if expected_expr != None:
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
                raise ParserError(self.file, f"if statement syntax is '[if][some expression]'", if_token.line, if_token.column_start, if_token.column_end)
            
            expected_expression = line[1:]

            expr_node = self.shunting_yard_algo(expected_expression)

            if_node = IFNode(condition=expr_node, meta_data=if_token) if if_token.type == TokenType.T_IF else ElifNode(condition=expr_node, meta_data=if_token)
            
            self.post_SYA.append(if_node)
    
    def handle_for_loop(self, line_idx):

        line = self.post_split[line_idx]

        for_token = line[0]
        if len(line) < 3:
            raise ParserError(self.file, f"for loop syntax is '[for][some identifier][some expression]'", for_token.line, for_token.column_start, for_token.column_end)
        
        variable_token = line[1]
        if variable_token.type != TokenType.T_IDENT:
            raise ParserError(self.file, f"for loop syntax is '[for][some identifier][some expression]'", variable_token.line, variable_token.column_start, variable_token.column_end)

        expected_expression = line[2:]

        variable_node = IdentifierNode(value=variable_token.value, meta_data=variable_token)
        expr_node = self.shunting_yard_algo(expected_expression)

        for_node = ForNode(variable=variable_node, bound=expr_node, meta_data=variable_token)

        self.post_SYA.append(for_node)

         
    def handle_while_loop(self, line_idx):
        line = self.post_split[line_idx]
        while_token = line[0]
        if len(line) < 2:
            raise ParserError(self.file, f"while loop syntax is '[while][some expression]'", while_token.line, while_token.column_start, while_token.column_end)
        
        expected_expression = line[1:]

        expr_node = self.shunting_yard_algo(expected_expression)

        while_node = WhileNode(condition=expr_node, meta_data=while_token)

        self.post_SYA.append(while_node)
    
    def handle_single_tokens(self, line_idx):

        line = self.post_split[line_idx]
        single_token = line[0]

        single_token_to_class = {
        TokenType.T_END:      EndNode,
        TokenType.T_BREAK:    BreakNode,
        TokenType.T_CONTINUE: ContinueNode,
    }
        single_node = single_token_to_class[single_token.type]

        single_node_class = single_node(single_token)

        self.post_SYA.append(single_node_class)

    def handle_function_def(self, line_idx):
        line = self.post_split[line_idx]
        
        single_token = line[0]
        if len(line) != 3:
            raise ParserError(self.file, "function declaration syntax is [fn][identifier][identifier]", single_token.line, single_token.column_start, single_token.column_end)
        
        expected_func_name = line[1]
        expected_args_name = line[2]
        
        if expected_args_name.type != TokenType.T_IDENT or expected_func_name.type != TokenType.T_IDENT:
            raise ParserError(self.file, "function declaration syntax is [fn][identifier][identifier]", single_token.line, single_token.column_start, single_token.column_end)
        
        function_node = FunctionNode(name=expected_func_name.value, arg_list_name=expected_args_name.value, meta_data=single_token)
        self.post_SYA.append(function_node)
    
    def handle_function_call(self, line, function_name):

        elements = []
        current = []
        depth = 0
        tok_idx = 1
        creators = []

        if type(function_name) != IdentifierNode:
            raise ParserError(self.file, "function call syntax is [identifier][{args1, args2, etc.}]]")
        
        while tok_idx < len(line):
            tok = line[tok_idx]

            if tok.type in self.DEPTH_CREATORS:
                # entering one more level of nested braces
                depth += 1
                current.append(tok)
                creators.append(tok)

            elif tok.type in self.DEPTH_ENDERS:
                if depth == 0:    
                    if current:
                        elements.append(self.shunting_yard_algo(current))
                    return CallNode(name=function_name.value,args=elements,meta_data=function_name.meta_data), tok_idx
                if (not creators or tok.type != self.DEPTH_CREATORS[creators[-1].type]):
                    raise ParserError(self.file, "mismatched brackets", tok.line, tok.column_start, tok.column_end)
                depth -= 1
                current.append(tok)
                creators.pop()

            elif tok.type == TokenType.T_COMMA and depth == 0:
                if current:
                    elements.append(self.shunting_yard_algo(current))
                current = []
            
            else:
                current.append(tok)

            tok_idx += 1
        # if creators dosent exist and we reach this point it means the first bracket which we dont track in creators wasn't closed
        raise ParserError(self.file, f"Unterminated {creators[0].value if creators else line[0].value}", line[0].line,line[0].column_start, line[0].column_end)



    
    def handle_return(self, line_idx):

        line = self.post_split[line_idx]
        return_token = line[0]
        if len(line) <= 1:
            raise ParserError(self.file, "Return statement syntax is [return][expression]", return_token.line, return_token.column_start, return_token.column_end)
        
        expected_expression = line[1:]

        expr_node = self.shunting_yard_algo(expected_expression)

        return_node = ReturnNode(meta_data=return_token, expression=expr_node)

        self.post_SYA.append(return_node)

    def handle_assignments(self, line, assignment_idx):

        valid_left_hands = {IndexNode, IdentifierNode}

        assignment_op_token = line[assignment_idx]
        left_hand = line[:assignment_idx]
        
        left_hand_node = self.shunting_yard_algo(left_hand).root_expr

        if type(left_hand_node) not in valid_left_hands:
            raise ParserError(self.file, "assignment statement syntax is [identifier][=][expression]", assignment_op_token.line, assignment_op_token.column_start, assignment_op_token.column_end)
        
        self.illegal_assignment = 1

        expected_expression = line[assignment_idx + 1:]

        expr_node = self.shunting_yard_algo(expected_expression)

        assignment_node = AssignmentNode(left_hand=left_hand_node, op=assignment_op_token.type, meta_data=assignment_op_token, right_hand=expr_node)

        self.post_SYA.append(assignment_node)

        self.illegal_assignment = 2
    
    def handle_index(self, base, line):
        # this must be updated any time a new index option is added to the lang
        NOT_INDEXABLE = {
            IntegerLiteralNode,
            FloatLiteralNode,
            NoneLiteralNode,
            BooleanLiteralNode
        }

        if type(base) in NOT_INDEXABLE:
            raise ParserError(self.file, f"Can't index into {base}", base.meta_data.line, base.meta_data.column_start, base.meta_data.column_end)
        
        left_bracket = line[0]
        depth = 0
        for tok_idx, tok in enumerate(line):
            if tok.type == TokenType.T_RBRACKET:
                depth -= 1
                if depth == 0:
                    expected_expression = line[1:tok_idx]
                    evaluated_expression = self.shunting_yard_algo(expected_expression)
                    if type(base) != IndexNode:
                        return IndexNode(base=base, index=[evaluated_expression], meta_data=left_bracket), tok_idx
                    else:
                        base.index.append(evaluated_expression)
                        return base, tok_idx
            elif tok.type == TokenType.T_LBRACKET:
                depth += 1
        raise ParserError(self.file, "Mismatched brackets", base.meta_data.line, base.meta_data.column_start, base.meta_data.column_end)


    # its really important to remember here that an array isn't an expression
    # in our langauge, its a container of expressions. this might be somewhat confusing
    # because if you pass an array into the SYA it will be wrapped in a expression node, but that is only
    # because its the root expression. all an expression node is in this lanaguge is the root of whatever is passed into
    # the SYA, which is why its attribute is root_expr
    def handle_array_literals(self, line):
        
        elements = []
        current = []
        depth = 0                   
        tok_idx = 1
        creators = []

        while tok_idx < len(line):
            
            tok = line[tok_idx]

            # ── open bracket ────────────────────────────────────────────────
            if tok.type in self.DEPTH_CREATORS:
                depth += 1
                current.append(tok)
                creators.append(tok)

            # ── close bracket ───────────────────────────────────────────────
            elif tok.type in self.DEPTH_ENDERS:
                if depth == 0:                     
                    if current:                      
                        elements.append(self.shunting_yard_algo(current))
                    return ArrayLiteralNode(elements, meta_data=line[0]), tok_idx
                if (not creators or tok.type != self.DEPTH_CREATORS[creators[-1].type]):
                    raise ParserError(self.file, "mismatched brackets", tok.line, tok.column_start, tok.column_end)
                depth -= 1
                current.append(tok)
                creators.pop()

            # ── comma that splits *top-level* elements ──────────────────────
            elif tok.type == TokenType.T_COMMA and depth == 0:
                if current:
                    elements.append(self.shunting_yard_algo(current))
                current = []
            # ── anything else (ident, number, +, etc.) ──────────────────────
            else:
                current.append(tok)

            tok_idx += 1
        
        raise ParserError(self.file, f"Unterminated {creators[0].value if creators else line[0].value}", line[0].line, line[0].column_start, line[0].column_end)
    
    def handle_string_literals(self, line):
        string_value = ""
        left_quote_lexeme = line[0]
        if len(line) <= 1:
            raise ParserError(self.file, "Mismatched string", left_quote_lexeme.line, left_quote_lexeme.column_start, left_quote_lexeme.column_end)
        rest_of_string = line[1:]
        # we ignore the tok because in the case of strings
        # we don't really care what's inside of them,
        # just that they're strings
        for tok_idx, ignored_tok in enumerate(rest_of_string):
            if ignored_tok.type == TokenType.T_STRING:
                return StringLiteralNode(value=string_value, meta_data=left_quote_lexeme), tok_idx + 1
            # remember in our lexeme definition we defined the lexeme value
            # to always be a string because we are always reading from a file/string
            # format so we don't have to do any type conversion here
            string_value += ignored_tok.value
        raise ParserError(self.file, "Mismatched string", left_quote_lexeme.line, left_quote_lexeme.column_start, left_quote_lexeme.column_end)
        


    # this is our expression handler
    # whenever we expect an expression in a different handler
    # we will pass the expected piece of our list of Lexemes
    # to this algo, which will either return a valid expression node
    # , or raise an error because the list wasn't a valid expression
    def shunting_yard_algo(self, line):
        output = []
        op_stack = []
        # whenever we get a potential expression
        # we need a custom algorithm to get rid of ambiguity in the +-!
        # operators since SYA can't handle them naturally
        # this does make our expression-level parser two-pass
        # but it avoids lexer hacks that would raise modularity and
        # clarity problems
        line = self.handle_unary_ambiguity(line)
        expect_operand = True
        # can_follow is a really elegant way to handle errors in the shunting yard algorithm
        # we essentially define a two-state transition, and based on our
        # current state we can either allow the next token, or throw an error
        # another important aspect to this transition is that not every operand expects an operator
        # whereas every operator expects an operand and so you can define an additional table
        # or information that defines each operand with a true or false value to determine whether 
        # it merits a state transition, but there are so few you can typically just if statement
        can_follow_operator = {
            TokenType.T_INT, TokenType.T_FLOAT, TokenType.T_BOOL, TokenType.T_NONE,
            TokenType.T_IDENT, 
            TokenType.T_LBRACKET, TokenType.T_LPAREN,
            TokenType.T_UMINUS, TokenType.T_UPLUS, TokenType.T_NEGATE,
            TokenType.T_STRING,
        }

        unary_ops = {
                TokenType.T_UPLUS,
                TokenType.T_UMINUS,
                TokenType.T_NEGATE,
            }

        can_follow_operand = (set(self.PRECEDENCE) - unary_ops) | {
                            TokenType.T_RPAREN,
                            TokenType.T_RBRACKET,
                            # this can follow an operand because in the case an array
                            # follows an operand it can be an index node
                            # if the operand isn't indexable we throw and error in the index handler
                            TokenType.T_LBRACKET,
                            TokenType.T_LBRACE,
                            TokenType.T_RBRACE
        }
        
        
        def apply_operator():

            op_tok = op_stack.pop()
            # unary
            if op_tok.type in unary_ops:
                operand = output.pop()
                output.append(UnaryOPNode(op=op_tok.type, meta_data=op_tok, operand=operand))
            else:
            # binary
                right = output.pop()
                left  = output.pop()
                output.append(BinOpNode(left=left, op=op_tok.type, meta_data=op_tok, right=right))

        # the while loop is really important; it can't be replaced
        # with a for loop because we want a simple way to skip entire portions of
        # code if we encounter a string, array, etc.
        tok_idx = 0
        while tok_idx < len(line):

            tok = line[tok_idx]

            if tok.type in self.ASSIGNMENT:
                if self.illegal_assignment:
                    raise ParserError(self.file, "illegal assignment", tok.line, tok.column_start, tok.column_end)

                self.handle_assignments(line, tok_idx)
                tok_idx = len(line)
                continue
            
            # ERROR CHECKING START

            # define the can_follow groups with all expression-level syntax
            # and so if a token isn't in these two, it isn't a token meant for expressions
            if tok.type not in can_follow_operand and tok.type not in can_follow_operator:
                raise ParserError(self.file, "token not allowed in expressions", tok.line, tok.column_start, tok.column_end)
            
            # we should naturally never come across an R bracket because that means we didn't come across
            # a LBRACKET first, and that merits an immediate error
            elif tok.type in [TokenType.T_RBRACKET, TokenType.T_RBRACE]:
                raise ParserError(self.file, "Mismatched grouping", tok.line, tok.column_start, tok.column_end)
            
            elif expect_operand:
                if tok.type not in can_follow_operator:
                    raise ParserError(self.file, f"Token not allowed to follow to follow operator or start expression", tok.line, tok.column_start, tok.column_end)
                                   # these token types are the operands mentioned above
                                   # that dont merit a state transition
                if tok.type not in [TokenType.T_LBRACKET, TokenType.T_LPAREN] and tok.type not in unary_ops:
                    expect_operand = False
                
            else:
                if tok.type not in can_follow_operand:
                    raise ParserError(self.file, f"Token not allowed to follow operand", tok.line, tok.column_start, tok.column_end)
                if tok.type not in [TokenType.T_LBRACKET, TokenType.T_RPAREN]:
                    expect_operand = True
                
            # ERROR CHECKING FINISHED

            # A) Literals & identifiers → output
            if tok.type in self._literal_map:
                output.append(self._literal_map[tok.type](tok))
                
            
            elif tok.type == TokenType.T_IDENT:
                output.append(IdentifierNode(value=tok.value, meta_data=tok))
                
            # handling array literal in seperate function
            elif tok.type == TokenType.T_LBRACKET:
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
                    base = output.pop()
                    idx_node, consumed = self.handle_index(base, line[tok_idx:])
                    output.append(idx_node)
                    tok_idx += consumed
                expect_operand = False
            elif tok.type == TokenType.T_LBRACE:
                function_name = output.pop()
                call_node, consumed = self.handle_function_call(line[tok_idx:], function_name)
                output.append(call_node)
                tok_idx += consumed
                expect_operand = False

              
            # C) Any operator
            elif tok.type in self.PRECEDENCE:
                p1 = self.PRECEDENCE[tok.type]
                assoc = self.ASSOCIATIVITY[tok.type]
                while op_stack and op_stack[-1].type in self.PRECEDENCE:
                    top = op_stack[-1]
                    p2 = self.PRECEDENCE[top.type]
                    if (assoc == 'left'  and p1 <= p2) or (assoc == 'right' and p1 <  p2):
                        apply_operator()
                    else:
                        break
                op_stack.append(tok)
            
            # D) Left grouping
            elif tok.type == TokenType.T_LPAREN:
                op_stack.append(tok)

            # F) right paren
            elif tok.type == TokenType.T_RPAREN:
                while op_stack and op_stack[-1].type != TokenType.T_LPAREN:
                    apply_operator()
                if not op_stack:
                    raise ParserError(self.file, "Mismatched grouping", tok.line, tok.column_start, tok.column_end)
                op_stack.pop()  # discard '('
            
            tok_idx += 1
        

        if self.illegal_assignment != 2:
            while op_stack:
                top = op_stack[-1]
                if top.type in { TokenType.T_LPAREN, TokenType.T_RPAREN}:
                    raise ParserError(self.file, "Mismatched grouping", top.line, top.column_start, top.column_end)
                if not output:
                    #this not outputting correct error msg
                    raise ParserError(self.file, "operator has no operand to bind to", top.line, top.column_start, top.column_end)
                apply_operator()
        
            root = output.pop()
            return ExpressionNode(root_expr=root)







