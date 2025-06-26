# after this pass, all of the user code will be interpreted through python.
# the user code will be evaluated until a runtime error or until the end of the code
# all we are doing here is simulating until one of these things happen

# this file shares many simulator with our semantic analyzer because in both we essentially just
# tree-walking; in the semantic analyzer we are tree walking for types, and in this we are tree walking for runtime values
import operator

from lexer import TokenType
from parser_nodes import (
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
    BreakNode,
    ContinueNode,
    EndNode,
    ReturnNode,
    ExpressionNode,
    FunctionNode,
    CallNode,
)

from semantic_nodes import (
    NumberType,
    BoolType,
    StringType,
    NoneType,
    ArrayType,
    IdentifierType,
    FunctionType,
    CallListType,
    DynamicType,
)

from evaluator_nodes import (
    runtime_function,
)

class EvaluatorError(Exception):

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
            f"[EvaluatorError] Line {self.row + 1}, Column {self.start}-{self.end}:\n"
            f"{error_line.rstrip()}\n"
            f"{pointers}\n"
            f"{self.msg}"
        )

    def __str__(self) -> str:
        return self._format()

    __repr__ = __str__


# from our semantic analysis, we don't have to really change anything.
# we are going to go to our leaf functions (the functions where any given dispatch could end)
# and we will return values instead of types. In the control flow statements, we will also add
# basic things that allow for simulation such as a for loop

class Evaluator:
    
    def __init__(self, file, roots):

        self.file = file
        self.roots = roots

        # same thing as in the semantic pass
        # we will have a bunch of scopes
        self.scope_stack = [{}]

        # we need to know the loop depth for the break/continue etc constructs
        # because if we see a break outside of a loop for example we can throw an error
        self.loop_depth = 0
        self.func_depth = 0

        self.literals = {
                    IntegerLiteralNode: int,
                    FloatLiteralNode: float,
                    StringLiteralNode: str,
                    # we will be converting booleans to
                    # zeroes and ones respectivley and none to zero
                    BooleanLiteralNode: int,
                    NoneLiteralNode: int,
                    }
        

        self.ARITH_OPS = {
            TokenType.T_PLUS, TokenType.T_MINUS,
            TokenType.T_ASTERISK, TokenType.T_SLASH,
            TokenType.T_DSLASH, TokenType.T_EXPO,
        }

        self.ARITH_ASSIGNMENTS = {
            TokenType.T_PLUS_ASSIGN, TokenType.T_MINUS_ASSIGN,
            TokenType.T_SLASH_ASSIGN, TokenType.T_ASTERISK_ASSIGN,
        }


        self.allowed_unary_ops = {
            int,
        }

        self.construct_to_eval = {
            AssignmentNode: self.eval_assignments,
            IFNode:         self.eval_if,
            ElifNode:       self.eval_elif,
            ElseNode:       self.eval_else,
            ForNode:        self.eval_for,
            WhileNode:      self.eval_while,
            BlockNode:      self.eval_block,
            BreakNode:      self.eval_break,
            ContinueNode:   self.eval_continue,
            ReturnNode:     self.eval_return,
            ExpressionNode: self.eval_expression,
            FunctionNode: self.eval_function,
            CallNode: self.eval_expression,
        }


    def eval_program(self):
        for construct in self.roots:
            self.eval_construct(construct)
    
    # could probably use this eval_construct more
    # typically but its clearer to just call the specific expression
    # in some cases although this could change
    def eval_construct(self, root):
        handler = self.construct_to_eval.get(type(root))
        return handler(root)
    
    def eval_function(self, root):
        function_name = root.name
        args_name = root.arg_list_name
        # its really important to initalize the function outside of its bodys scope

        self.initalize_var(function_name, FunctionType(value=root.body))

        self.func_depth += 1
        self.scope_stack.append({})
        self.initalize_var(args_name, CallListType(value=[]))

        self.eval_block(root.body)
        self.scope_stack.pop()
        self.func_depth -= 1
        
    def eval_block(self, root):
        # A block just evals its children in the current scope

        for construct in root.block:
            self.eval_construct(construct)
    
    def eval_if(self, root):

        self.eval_expression(root.condition.root_expr)
        self.scope_stack.append({})
        self.eval_block(root.body)
        self.scope_stack.pop()

        for elif_root in root.elif_branch.block:
            self.eval_elif(elif_root)
        for else_root in root.else_branch.block:
            self.eval_else(else_root)
    
    def eval_elif(self, root):

        self.eval_expression(root.condition.root_expr)
        self.scope_stack.append({})
        self.eval_block(root.body)
        self.scope_stack.pop()
    
    def eval_else(self, root):
        self.scope_stack.append({})
        self.eval_block(root.body)
        self.scope_stack.pop()
    
    
    def eval_for(self, root):
        self.loop_depth += 1
        self.scope_stack.append({})
        left_hand_name = root.variable.value
        right_hand_type = self.eval_expression(root.bound.root_expr)
        if type(right_hand_type) in {StringType, NoneType}:
            raise EvaluatorError(self.file, "For loop bound must be an array, identifier, or number", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end)
        self.initalize_var(left_hand_name, right_hand_type)
        self.eval_block(root.body)
        self.scope_stack.pop()
        self.loop_depth -= 1
    
    
    def eval_while(self, root):
        self.loop_depth += 1
        self.eval_expression(root.condition.root_expr)
        self.eval_block(root.body)
        self.loop_depth -= 1

    def eval_break(self, root):
        if self.loop_depth == 0:
            raise EvaluatorError(self.file, "cannot break outside of loop scope", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end)
    
    def eval_continue(self, root):
        if self.loop_depth == 0:
            raise EvaluatorError(self.file, "cannot continue outside of loop scope", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end)
    
    def eval_return(self, root):
        if not self.func_depth:
            raise EvaluatorError(self.file, "cannot return outside of function scope", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end)
        if root.expression:
            self.eval_expression(root.expression.root_expr)


    # every time a var is assigned we throw it into our current scope
    # to let expressions which use the var in the future know that exists in the current scope
    # with each initalized var being associated with its respective type 
    def initalize_var(self, left_hand, right_hand):

        #print(f"left_hand: {left_hand}")
        #print(f"right_hand: {right_hand}")
        #print(f"scope: {self.scope_stack}")

        self.scope_stack[-1][left_hand] = right_hand
    
    def search_for_var(self, name, potential_error):
        for scope in reversed(self.scope_stack):
            if name in scope:
                return scope[name]
        raise EvaluatorError(self.file, f"Variable {name} not found in current scope", potential_error.line, potential_error.column_start, potential_error.column_end)


    def eval_assignments(self, root):

        # probably we are going to want to change these if elif blocks into
        # functions because they are simply meant to differentiate between different types of 
        # left hands which could be arbitrarily large
        right_hand_type = self.eval_expression(root.right_hand.root_expr)
        op_type = root.op
        if type(root.left_hand) == IdentifierNode:
            left_hand_name = root.left_hand.value
            if op_type in self.ARITH_ASSIGNMENTS:
                left_hand_type = self.search_for_var(left_hand_name)
                if not left_hand_type:
                    raise EvaluatorError(self.file, "variable not initialized", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end)
                if (not ((type(right_hand_type) in [NumberType, BoolType] and type(left_hand_type) in [NumberType, BoolType]) or type(left_hand_type) == type(right_hand_type))):
                    raise EvaluatorError(self.file, "Invalid operation", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end)
            self.initalize_var(left_hand_name, right_hand_type)
        # else for now but with the addition of more assignable types
        # this will turn into an elif or a seperate function
        # **if type(left_hand) == IndexNode
        else:
            left_hand_type = self.eval_expression(root.left_hand)
            if left_hand_type.value != None and right_hand_type.value != None:
                if not left_hand_type:
                    raise EvaluatorError(self.file, "variable not initialized", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end)
                if (not ((type(right_hand_type) in [NumberType, BoolType] and type(left_hand_type) in [NumberType, BoolType]) or type(left_hand_type) == type(right_hand_type))):
                    raise EvaluatorError(self.file, "Invalid operation", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end)



    # where our dispatch always ends
    def eval_expression(self, root):
        
        if type(root) in self.literals:
            # converting bang literals to python literals
            actual_value_function = self.literals[type(root)]
            return actual_value_function(root.value)
        
        elif type(root) == BinOpNode:

            op = root.op

            left = self.eval_expression(root.left)
            right = self.eval_expression(root.right)
            
            return self.eval_bin_ops(left, op, right)
        
        elif type(root) == UnaryOPNode:

            op = self.eval_expression(root.operand)

            return self.eval_unary_ops(root.op, op)
        
        elif type(root) == ArrayLiteralNode:

            return [self.eval_expression(i) for i in root.elements]

        elif type(root) == IndexNode:

            base = self.eval_expression(root.base)
            for i in root.index:
                try:
                    base = base[i]
                except:
                    raise EvaluatorError(self.file, "Index out of bounds", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end)
            return base

        
        elif type(root) == IdentifierNode:
            # making sure each identifier is defined if its used in a given scope
            return self.search_for_var(root.value, root.meta_data)


        elif type(root) == CallNode:
            callee_type = self.search_for_var(root.name)
            if not callee_type:
                raise EvaluatorError(self.file, f"function not initalized'{root.name}'", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end,)
            if type(callee_type) != FunctionType:
                raise EvaluatorError(self.file, f"attempt to call non-function '{root.name}'", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end,)

            # Analyse each argument expression normally.
            for arg in root.args:
                self.eval_expression(arg.root_expr)
            
            return DynamicType()

    def eval_bin_ops(self, left, op, right):

        def eval_int_bin_op(self, left, op, right):
            # every supported operation between two ints in bang
            supported_types = {
                            TokenType.T_PLUS: operator.add, 
                            TokenType.T_MINUS: operator.sub, 
                            TokenType.T_ASTERISK: operator.mul, 
                            TokenType.T_SLASH: operator.truediv,
                            TokenType.T_DSLASH: operator.floordiv,
                            TokenType.T_EXPO: operator.pow,

                            TokenType.T_EQ: operator.eq,
                            TokenType.T_NEQ: operator.ne,

                            TokenType.T_LT: operator.lt,
                            TokenType.T_LEQ: operator.le,
                            TokenType.T_GT: operator.gt,
                            TokenType.T_GTEQ: operator.ge,
                                
                            TokenType.T_AND:     lambda a, b: a and b,
                            TokenType.T_OR:      lambda a, b: a or  b,
                                }
            
            if op in (TokenType.T_SLASH, TokenType.T_DSLASH) and right == 0:
                raise EvaluatorError(self.file, f"division by zero", op.meta_data.line, op.meta_data.column_start, op.meta_data.column_end,)
                
            if op not in supported_types:
                raise EvaluatorError(self.file, f"operation '{op.value}' not supported between type {type(left)} and type {type(right)}", op.meta_data.line, op.meta_data.column_start, op.meta_data.column_end,)
            
            return supported_types[op](left, right)
        
        def eval_str_bin_op(self, left, op, right):

            def str_sub(self, a, b):
                return a.replace(b, "")
            
            def str_div(self, a, b):
                return a.split(b)


            supported_types = {

                TokenType.T_PLUS: operator.add,
                TokenType.T_MINUS: str_sub,
                TokenType.T_SLASH: str_div,

                TokenType.T_LT: operator.lt,
                TokenType.T_LEQ: operator.le,
                TokenType.T_GT: operator.gt,
                TokenType.T_GTEQ: operator.ge,

                TokenType.T_EQ: operator.eq,
                TokenType.T_NEQ: operator.ne,

                TokenType.T_AND:     lambda a, b: a and b,
                TokenType.T_OR:      lambda a, b: a or  b,

            }
            
            if op not in supported_types:
                raise EvaluatorError(self.file, f"operation '{op.value}' not supported between type {type(left)} and type {type(right)}", op.meta_data.line, op.meta_data.column_start, op.meta_data.column_end,)
            
            return supported_types[op](left, right)
        
        def eval_list_bin_op(self, left, op, right):

            def list_sub(self, a, b):
                to_remove = set(b)
                return [x for x in a if x not in to_remove]
            
            def list_mul(self, a, b):
                if type(a) == list and type(b) == list:
                    if len(a) != len(b):
                        if 1 not in [len(a), len(b)]:
                            raise EvaluatorError(self.file, "list element-wise multiplication is not supported between lists of different lengths where" \
                                                "multiplicand length is not one", op.meta_data.line, op.meta_data.column_start, op.meta_data.column_end,
                                                )
                        multiplier = b[0] if len(b) == 1 else a[0]
                        base = a if len(a) != 1 else b
                        return [x * multiplier for x in base]
                    else:
                        return [i * j for i, j in zip(a, b)]
                else:
                    # this will be where operations such as [1] * 3 go which we will need to change semantic pass to allow
                    pass
                        
                    
            def list_div(self, a, b):
                if type(a) == list and type(b) == list:
                    if len(a) != len(b):
                        if 1 not in [len(a), len(b)]:
                            raise EvaluatorError(self.file, "list element-wise divsion is not supported between lists of different lengths where" \
                                                "divisor length is not one", op.meta_data.line, op.meta_data.column_start, op.meta_data.column_end,
                                                )
                        divisor = b[0] if len(b) == 1 else a[0]
                        base = a if len(a) != 1 else b
                        return [x / divisor for x in base]
                    else:
                        return [i / j for i, j in zip(a, b)]
                    
            def list_floor_div(self, a, b):
                if type(a) == list and type(b) == list:
                    if len(a) != len(b):
                        if 1 not in [len(a), len(b)]:
                            raise EvaluatorError(self.file, "list element-wise divsion is not supported between lists of different lengths where" \
                                                "divisor length is not one", op.meta_data.line, op.meta_data.column_start, op.meta_data.column_end,
                                                )
                        divisor = b[0] if len(b) == 1 else a[0]
                        base = a if len(a) != 1 else b
                        return [x // divisor for x in base]
                    else:
                        return [i // j for i, j in zip(a, b)]

            supported_types = {

                TokenType.T_PLUS: operator.add,
                TokenType.T_MINUS: list_sub,
                TokenType.T_ASTERISK: list_mul,
                TokenType.T_SLASH: list_div,
                TokenType.T_DSLASH: list_floor_div,
                TokenType.T_LT: operator.lt,
                TokenType.T_LEQ: operator.le,
                TokenType.T_GT: operator.gt,
                TokenType.T_GTEQ: operator.ge,

                TokenType.T_EQ: operator.eq,
                TokenType.T_NEQ: operator.ne,

                TokenType.T_AND:     lambda a, b: a and b,
                TokenType.T_OR:      lambda a, b: a or  b,
            }

        type_dispatch = {
            int: eval_int_bin_op,
            str: eval_str_bin_op,
            list: eval_list_bin_op,
        }

        dispatcher = type_dispatch.get(type(left))
        return dispatcher(left, op, right)
    
    def eval_unary_ops(self, operator, operand):
        
        # since each unary operation is pretty clear on what it does
        # we will dispatch based on unary operator not type

        operator_dispatch = {
            TokenType.T_NEGATE: eval_negate,
            TokenType.T_UMINUS: eval_uminus,
            TokenType.T_UPLUS: eval_uplus,
        }

        def eval_negate(self, operand):
            return not operand
        
        def eval_uminus(self, operand):
            if type(operand) == int:
                return -operand
            raise EvaluatorError(self.file, f"unary negation not supported on type {type(operand)}",operator.meta_data.line, operator.meta_data.column_start, operator.meta_data.column_end)
        
        def eval_uplus(self, operand):

            if type(operand) == int:
                return abs(operand)
            raise EvaluatorError(self.file, f"unary plus not supported on type {type(operand)}",operator.meta_data.line, operator.meta_data.column_start, operator.meta_data.column_end)

