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

# when we encounter a break, return, etc we
# need to propogate this across potentially every function we have; so instead of returning
# "break_signal" and adding custom logic to each one, which increases the complexity and
# decreases readability, we create private exceptions that allow us to control exactly where each signal
# propogates to

class _ReturnSignal(Exception):
    __slots__ = ("value",)
    def __init__(self, value): self.value = value          # carry the result

class _BreakSignal(Exception):
    pass

class _ContinueSignal(Exception):
    pass


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

        def _built_in_print(args, meta_data):
            print(*args)
        
        def _built_in_len(args, meta_data):
            if len(args) != 1:
                raise EvaluatorError(self.file,"len expects exactly one arg", meta_data.line, meta_data.column_start, meta_data.column_end)
            if type (args[0]) not in [str, list]:
                raise EvaluatorError(self.file,f"len expects list, str, not {type(args[0])}", meta_data.line, meta_data.column_start, meta_data.column_end)
            return len(args[0])
        
        def _built_in_sum(args, meta_data):
            if not args:
                raise EvaluatorError(self.file, "sum function expects argument list of at least length one", meta_data.line, meta_data.column_start, meta_data.column_end)
            if len(args) == 1:
                if type(args[0]) in [str, list]:
                    args = args[0]
                else:
                    return args[0]
            expected_type = type(args[0])
            if expected_type == int:
                base = 0
            elif expected_type == str:
                base = ""
            elif expected_type == list:
                base = []
            for i in args:
                if type(i) != expected_type:
                    raise EvaluatorError(self.file, "sum function expects argument list of homegenous type", meta_data.line, meta_data.column_start, meta_data.column_end)
                base += i
            return base
        
        def _built_in_min(args, meta_data):
            if not args:
                raise EvaluatorError(self.file, "min function expects argument list of at least length one", meta_data.line, meta_data.column_start, meta_data.column_end)
            if len(args) == 1:
                if type(args[0]) in [str, list]:
                    args = args[0]
                else:
                    return args[0]
            expected_type = type(args[0])
            base = args[0]
            for i in args:
                if type(i) != expected_type:
                    raise EvaluatorError(self.file, "min function expects argument list of homegenous type", meta_data.line, meta_data.column_start, meta_data.column_end)
                base = min(base, i)
            return base

        def _built_in_max(args, meta_data):
            if not args:
                raise EvaluatorError(self.file, "max function expects argument list of at least length one", meta_data.line, meta_data.column_start, meta_data.column_end)
            if len(args) == 1:
                if type(args[0]) in [str, list]:
                    args = args[0]
                else:
                    return args[0]
            expected_type = type(args[0])
            base = args[0]
            for i in args:
                if type(i) != expected_type:
                    raise EvaluatorError(self.file, "max function expects argument list of homegenous type", meta_data.line, meta_data.column_start, meta_data.column_end)
                base = max(base, i)
            return base
        
        self.built_in_functions = {
            "print": _built_in_print,
            "len": _built_in_len,
            "sum": _built_in_sum,
            "min": _built_in_min,
            "max": _built_in_max,
        }
            

        self.scope_stack[0].update(self.built_in_functions)


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
                    NoneLiteralNode: lambda _ : 0,
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
            #ElifNode:       self.eval_elif,
            #ElseNode:       self.eval_else,
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

        self.initalize_var(function_name, runtime_function(body=root.body, params_name=args_name, closure=[i.copy() for i in self.scope_stack]))
        
    def eval_block(self, root):
        # A block just evals its children in the current scope

        for construct in root.block:
            self.eval_construct(construct)
    
    def eval_if(self, root):

        if self.eval_expression(root.condition.root_expr):
            self.scope_stack.append({})
            self.eval_block(root.body)
            self.scope_stack.pop()
            return
        for elif_root in root.elif_branch.block:
            if self.eval_expression(elif_root.condition.root_expr):
                self.scope_stack.append({})
                self.eval_block(elif_root.body)
                self.scope_stack.pop()
                return
        for else_root in root.else_branch.block:
            self.scope_stack.append({})
            self.eval_block(else_root.body)
            self.scope_stack.pop()
            return
    
    #def eval_elif(self, root):

        #self.eval_expression(root.condition.root_expr)
        #self.scope_stack.append({})
        #self.eval_block(root.body)
        #self.scope_stack.pop()
    
    #def eval_else(self, root):
        #self.scope_stack.append({})
        #self.eval_block(root.body)
        #self.scope_stack.pop()
    
    
    def eval_for(self, root):

        self.loop_depth += 1
        self.scope_stack.append({})
        left_hand_name = root.variable.value

        right_hand_val = self.eval_expression(root.bound.root_expr)
        if len(left_hand_name) >= 5 and left_hand_name.lower()[:5] == "range":
            if type(right_hand_val) != list:
                raise EvaluatorError(self.file, "range loop can only be accessed with bound of type list", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end)
            if len(right_hand_val) == 1:
                start = 0
                end = right_hand_val[0]
                jump = 1
            elif len(right_hand_val) == 2:
                start = right_hand_val[0]
                end = right_hand_val[1]
                jump = 1
            else:
                start = right_hand_val[0]
                end = right_hand_val[1]
                jump = right_hand_val[2]
            if not all(isinstance(i, (int)) for i in (start, end, jump)):
                raise EvaluatorError(self.file, "start, end, and jump of range list (first three elements) must be integers", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end)
            for i in range(start, end, jump):
                self.initalize_var(left_hand_name, i)
                try:
                    self.eval_block(root.body)
                except _ContinueSignal:
                    continue
                except _BreakSignal:
                    break
        elif type(right_hand_val) == int:
            for i in range(0, right_hand_val, -1 if right_hand_val < 0 else 1):
                self.initalize_var(left_hand_name, i)
                try:
                    self.eval_block(root.body)
                except _ContinueSignal:
                    continue
                except _BreakSignal:
                    break
        else:
            try:
                for i in right_hand_val:
                    self.initalize_var(left_hand_name, i)
                    try:
                        self.eval_block(root.body)
                    except _ContinueSignal:
                        continue
                    except _BreakSignal:
                        break
            except:
                raise EvaluatorError(self.file, "bound not iterable", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end)
        self.scope_stack.pop()
        self.loop_depth -= 1


    def eval_while(self, root):
        self.loop_depth += 1
        self.scope_stack.append({})
        try:
            while self.eval_expression(root.condition.root_expr):
                try:
                    self.eval_block(root.body)
                except _BreakSignal:
                    break
                except _ContinueSignal:
                    continue
        finally:
            self.loop_depth -= 1
            self.scope_stack.pop()

    def eval_break(self, root):
        if self.loop_depth == 0:
            raise EvaluatorError(self.file, "cannot break outside of loop scope", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end)
        raise _BreakSignal()
    
    def eval_continue(self, root):
        if self.loop_depth == 0:
            raise EvaluatorError(self.file, "cannot continue outside of loop scope", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end)
        raise _ContinueSignal()
    
    def eval_return(self, root):
        if not self.func_depth:
            raise EvaluatorError(self.file, "cannot return outside of function scope", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end)
        value = self.eval_expression(root.expression.root_expr)
        raise _ReturnSignal(value=value)


    # every time a var is assigned we throw it into our current scope
    # to let expressions which use the var in the future know that exists in the current scope
    # with each initalized var being associated with its respective type 
    def initalize_var(self, left_hand, right_hand):

        #print(f"left_hand: {left_hand}")
        #print(f"right_hand: {right_hand}")
        #print(f"scope: {self.scope_stack}")

        self.scope_stack[-1][left_hand] = right_hand
    
    def search_for_var(self, name, potential_error):
        for idx, scope in enumerate(reversed(self.scope_stack)):
            if name in scope:
                #converts reversed index to normal index
                return len(self.scope_stack) - idx - 1
        raise EvaluatorError(self.file, f"Variable {name} not found in current scope", potential_error.line, potential_error.column_start, potential_error.column_end)


    def eval_assignments(self, root):

        # probably we are going to want to change these if elif blocks into
        # functions because they are simply meant to differentiate between different types of 
        # left hands which could be arbitrarily large

        assignment_to_normal_ops = {
            TokenType.T_PLUS_ASSIGN: TokenType.T_PLUS,
            TokenType.T_MINUS_ASSIGN: TokenType.T_MINUS,
            TokenType.T_SLASH_ASSIGN: TokenType.T_SLASH,
            TokenType.T_ASTERISK_ASSIGN: TokenType.T_ASTERISK,
        }

        right_hand_value = self.eval_expression(root.right_hand.root_expr)
        op_type = root.op

        if op_type != TokenType.T_ASSIGN:
            left_hand_value = self.eval_expression(root.left_hand)
            right_hand_value = self.eval_expression(BinOpNode(left=root.left_hand, op=assignment_to_normal_ops[op_type], right=root.right_hand.root_expr, meta_data=root.meta_data))

        if type(root.left_hand) == IdentifierNode:
            left_hand_name = root.left_hand.value
            try:
                 idx = self.search_for_var(left_hand_name, root.meta_data)
                 self.scope_stack[idx][left_hand_name] = right_hand_value
            except:
                self.initalize_var(left_hand_name, right_hand_value)
            return
        else:
            if type(root.left_hand.base) == IdentifierNode:
                base_location = self.search_for_var(root.left_hand.base.value, root.meta_data)
                base_frame = self.scope_stack[base_location]
                target = base_frame[root.left_hand.base.value]
                for idx in root.left_hand.index[:-1]:
                    try:
                        target = target[self.eval_expression(idx.root_expr)]
                    except:
                        raise EvaluatorError(self.file, "Index out of bounds", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end)
                try:
                    final_idx = self.eval_expression(root.left_hand.index[-1].root_expr)
                    target[final_idx] = right_hand_value
                except:
                    raise EvaluatorError(self.file, "Index out of bounds", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end) 
            else:
                raise EvaluatorError(self.file, "unassignable entity", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end)
            
    # this function handles all expression level contructs such as literals, binary ops,
    # unary ops, and function calls
    def eval_expression(self, root):
        if type(root) == ExpressionNode:
            root = root.root_expr

        if type(root) in self.literals:
            # converting bang literals to python literals
            actual_value_function = self.literals[type(root)]
            return actual_value_function(root.value)
        
        elif type(root) == BinOpNode:
            # converting bang binary operation into a python literal
            return self.eval_bin_ops(root)
        
        elif type(root) == UnaryOPNode:
            # converting bang unary operation into a python literal
            return self.eval_unary_ops(root)
        
        elif type(root) == ArrayLiteralNode:
            # converting bang list into python list of python literals
            return [self.eval_expression(i.root_expr) for i in root.elements]

        elif type(root) == IndexNode:
            # converting bang index into python literal
            index_chain = [self.eval_expression(i.root_expr) for i in root.index]
            base = self.eval_expression(root.base)
            for i in index_chain:
                try:
                    base = base[i]
                except:
                    raise EvaluatorError(self.file, "Index out of bounds", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end)
            return base

        
        elif type(root) == IdentifierNode:
            # converting every bang identifier into a python literal
            return self.scope_stack[self.search_for_var(root.value, root.meta_data)][root.value]

        elif type(root) == CallNode:
            # executing a bang block
            callee = self.scope_stack[self.search_for_var(root.name, root.meta_data)][root.name]
            arg_vals = [self.eval_expression(i.root_expr) for i in root.args]


            if callable(callee) and root.name in self.built_in_functions:
                return self.built_in_functions[root.name](arg_vals, root.meta_data)


            if type(callee) == runtime_function:
                return self.eval_call(callee, arg_vals, root.meta_data)


            
            return self.eval_call(callee, arg_vals, root.meta_data)
    

    #-------------------------------------------
    # BINARY OPERATIONS START
    #-------------------------------------------

    def eval_bin_ops(self, root):
         
        op = root.op

        left = self.eval_expression(root.left)
        right = self.eval_expression(root.right)

        #-------------------------------------------
        # INT OPERATIONS START
        #-------------------------------------------

        def eval_int_bin_op(left, op, right):
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
                raise EvaluatorError(self.file, f"division by zero", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end,)
                
            if op not in supported_types:
                raise EvaluatorError(self.file, f"operation '{op.value}' not supported between type {type(left)} and type {type(right)}", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end,)
            
            return supported_types[op](left, right)
        
        #-------------------------------------------
        # INT OPERATIONS END
        #-------------------------------------------
        
        #-------------------------------------------
        # STRING OPERATIONS START
        #-------------------------------------------
        
        def eval_str_bin_op(left, op, right):

            def str_sub(a, b):
                return a.replace(b, "")
            
            def str_div(a, b):
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
                raise EvaluatorError(self.file, f"operation '{op.value}' not supported between type {type(left)} and type {type(right)}", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end)
            
            return supported_types[op](left, right)
        
        #-------------------------------------------
        # STRING OPERATIONS END
        #-------------------------------------------
        
        #-------------------------------------------
        #LIST OPERATIONS START
        #-------------------------------------------
        
        def eval_list_bin_op(left, op, right):

            def list_div_helper(a,b,div_type):
                    if b == 0:
                        raise EvaluatorError (self.file, "attempted divison by zero", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end)
                    return a / b if div_type == "true" else a // b

            def list_sub(a, b):
                to_remove = set(b)
                return [x for x in a if x not in to_remove]
            
            def list_mul(a, b):
                if type(a) == list and type(b) == list:
                    if len(a) != len(b):
                        if 1 not in [len(a), len(b)]:
                            raise EvaluatorError(self.file, "list element-wise multiplication is not supported between lists of different lengths where" \
                                                "multiplicand length is not one", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end
                                                )
                        multiplier = b[0] if len(b) == 1 else a[0]
                        base = a if len(a) != 1 else b
                        return [x * multiplier for x in base]
                    else:
                        return [i * j for i, j in zip(a, b)]
                else:
                    # this will be where operations such as [1] * 3 go which we will need to change semantic pass to allow
                    pass
                        
                    
            def list_div(a, b):


                if type(a) == list and type(b) == list:
                    if len(a) != len(b):
                        if 1 not in [len(a), len(b)]:
                            raise EvaluatorError(self.file, "list element-wise divsion is not supported between lists of different lengths where" \
                                                "divisor length is not one", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end
                                                )
                        divisor = b[0] if len(b) == 1 else a[0]
                        base = a if len(a) != 1 else b
                        return [list_div_helper(x, divisor, "true") for x in base]
                    else:
                        return [list_div_helper(i, j, "true") for i, j in zip(a, b)]
                    
            def list_floor_div(a, b):
                if type(a) == list and type(b) == list:
                    if len(a) != len(b):
                        if 1 not in [len(a), len(b)]:
                            raise EvaluatorError(self.file, "list element-wise divsion is not supported between lists of different lengths where" \
                                                "divisor length is not one", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end
                                                )
                        divisor = b[0] if len(b) == 1 else a[0]
                        base = a if len(a) != 1 else b
                        return [list_div_helper(x, divisor, "floor") for x in base]
                    else:
                        return [list_div_helper(i, j, "floor") for i, j in zip(a, b)]
            


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

            if op not in supported_types:
                raise EvaluatorError(self.file, f"operation '{op.value}' not supported between type {type(left)} and type {type(right)}", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end)
            return supported_types[op](left, right)
        #-------------------------------------------
        #LIST OPERATIONS END
        #-------------------------------------------

        def eval_different_bin_op(left, op, right):


            supported_types = {
                TokenType.T_ASTERISK: operator.mul,

                TokenType.T_EQ: operator.eq,
                TokenType.T_NEQ: operator.ne,
                TokenType.T_AND:     lambda a, b: a and b,
                TokenType.T_OR:      lambda a, b: a or  b,
            }
            
            if op not in supported_types:
                raise EvaluatorError(self.file, f"operation '{op.value}' not supported between type {type(left)} and type {type(right)}", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end)
            
            return supported_types[op](left, right)
            


        type_dispatch = {
            int: eval_int_bin_op,
            float: eval_int_bin_op,
            str: eval_str_bin_op,
            list: eval_list_bin_op,
        }
        same_type = [int, float]
        dispatcher = eval_different_bin_op
        if type(left) == type(right) or (type(left) in same_type and type(right) in same_type):
            dispatcher = type_dispatch.get(type(left))
        return dispatcher(left, op, right)
    #-------------------------------------------
    # BINARY OPERATIONS END
    #-------------------------------------------


    #-------------------------------------------
    # UNARY OPERATIONS START
    #-------------------------------------------
    
    def eval_unary_ops(self, root):

        # since each unary operation is pretty clear on what it does
        # we will dispatch based on unary operator not type

        def eval_negate(operand):
            return not operand
        
        def eval_uminus(operand):
            if type(operand) in [int, float]:
                return -operand
            raise EvaluatorError(self.file, f"unary negation not supported on type {type(operand)}",root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end)
        
        def eval_uplus(operand):

            if type(operand) in [int, float]:
                return +operand
            raise EvaluatorError(self.file, f"unary plus not supported on type {type(operand)}",root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end)
        
        operator_dispatch = {
            TokenType.T_NEGATE: eval_negate,
            TokenType.T_UMINUS: eval_uminus,
            TokenType.T_UPLUS: eval_uplus,
        }
        operator = root.op
        operand = self.eval_expression(root.operand)
        return operator_dispatch[operator](operand)
    #-------------------------------------------
    # UNARY OPERATIONS END
    #-------------------------------------------

    
    def eval_call(self, callee, args, meta_data):

        saved_stack = self.scope_stack
        self.scope_stack = [i.copy() for i in callee.closure] + [{}]
        self.func_depth += 1
        try:
            self.initalize_var(callee.params_name, args)
            try:
                self.eval_block(callee.body)
            except _ReturnSignal as sig:
                return sig.value
        finally:
            self.scope_stack = saved_stack
            self.func_depth -= 1
        return 0



