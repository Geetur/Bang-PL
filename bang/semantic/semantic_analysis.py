# ONLY APPLIES TO STATICALLY KNOWABLE THINGS
# after this pass we are every variable is guaranteed to be defined before use; 
# every break, continue, return, is guaranteed to bee associated with a loop/function;
# all indexes are guaranteed to be numbers;
# all bin ops and unary ops are guaranteed to be valid if performed on literals
# every error that can be statically determined is determined.
from typing import Any
from bang.lexing.lexer import TokenType
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
    BreakNode,
    ContinueNode,
    EndNode,
    ReturnNode,
    ExpressionNode,
    FunctionNode,
    CallNode,
)

from bang.semantic.semantic_nodes import (
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

class SemanticError(Exception):

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
            f"[SemanticError] Line {self.row + 1}, Column {self.start}-{self.end}:\n"
            f"{error_line.rstrip()}\n"
            f"{pointers}\n"
            f"{self.msg}"
        )

    def __str__(self) -> str:
        return self._format()

    __repr__ = __str__

class SemanticAnalysis:
    
    def __init__(self, file, roots):
        self.file = file
        self.roots = roots

        # the scope stack is the only semi confusing thing about semantic analysis really, everything else
        # is just psuedo-intepreting to type check. but really all were doing is saying, if we enter a new scope, push 
        # a new scope level to our stack, if we exit a scope, pop a scope off our stack.
        # if we see an assignment, record the assignment in our current scope level.

        self.scope_stack = [{}]

        self.built_in_functions = {
            "print": FunctionType,
            "len": FunctionType,
            "sum": FunctionType,
            "min": FunctionType,
            "max": FunctionType,
            "sort": FunctionType,
            "set": FunctionType,
            "dict": FunctionType,
        }

        self.scope_stack[0].update(
                        {name: FunctionType(value=None) for name in self.built_in_functions}
        )
        
    

        # we need to know the loop depth for the break/continue etc constructs
        # because if we see a break outside of a loop for example we can throw an error
        self.loop_depth = 0
        self.func_depth = 0

        self.literals = {
                    IntegerLiteralNode: NumberType,
                    FloatLiteralNode: NumberType,
                    StringLiteralNode: StringType,
                    BooleanLiteralNode: BoolType,
                    NoneLiteralNode: NoneType,
                    }
        

        self.ARITH_OPS = {
            TokenType.T_PLUS, TokenType.T_MINUS,
            TokenType.T_ASTERISK, TokenType.T_SLASH,
            TokenType.T_DSLASH, TokenType.T_EXPO,
        }

        self.assignment_to_normal = {
           TokenType.T_PLUS_ASSIGN: TokenType.T_PLUS,
           TokenType.T_MINUS_ASSIGN: TokenType.T_MINUS,
           TokenType.T_ASTERISK_ASSIGN: TokenType.T_ASTERISK,
           TokenType.T_SLASH_ASSIGN: TokenType.T_SLASH,
        }

        self.ARITH_ASSIGNMENTS = {
            TokenType.T_PLUS_ASSIGN, 
            TokenType.T_MINUS_ASSIGN,
            TokenType.T_SLASH_ASSIGN, 
            TokenType.T_ASTERISK_ASSIGN,
        }


        self.allowed_unary_ops = {
            NumberType,
        }

        # boolean operations with specific constraints such as in operator
        # must have an iterable right hand
        self.BOOL_OP_RULES = {
            (NumberType, ArrayType, TokenType.T_IN),
            (BoolType, ArrayType, TokenType.T_IN),
            (StringType, ArrayType, TokenType.T_IN),
            (ArrayType, ArrayType, TokenType.T_IN),

            (StringType, StringType, TokenType.T_IN),
            

        }

        self.BIN_OP_DIFFERENT_RULES = {
            # I honestly should just merge number type and booltype
            # but thatll be for another day
            (StringType, NumberType, TokenType.T_ASTERISK): StringType,
            (NumberType, StringType, TokenType.T_ASTERISK): StringType,
            (StringType, BoolType, TokenType.T_ASTERISK): StringType,
            (BoolType, StringType, TokenType.T_ASTERISK): StringType,

            (ArrayType, NumberType, TokenType.T_ASTERISK): ArrayType,
            (NumberType, ArrayType, TokenType.T_ASTERISK): ArrayType,
            (ArrayType, BoolType, TokenType.T_ASTERISK): ArrayType,
            (BoolType, ArrayType, TokenType.T_ASTERISK): ArrayType,
        }

        self.construct_to_walk = {
            AssignmentNode: self.walk_assignments,
            IFNode:         self.walk_if,
            ElifNode:       self.walk_elif,
            ElseNode:       self.walk_else,
            ForNode:        self.walk_for,
            WhileNode:      self.walk_while,
            BlockNode:      self.walk_block,
            BreakNode:      self.walk_break,
            ContinueNode:   self.walk_continue,
            ReturnNode:     self.walk_return,
            ExpressionNode: self.walk_expression,
            FunctionNode: self.walk_function,
            CallNode: self.walk_expression,
        }


    def walk_program(self):
        for construct in self.roots:
            self.walk_construct(construct)
    
    # could probably use this walk_construct more
    # typically but its clearer to just call the specific expression
    # in some cases although this could change
    def walk_construct(self, root):
        handler = self.construct_to_walk.get(type(root))
        return handler(root)
    
    def walk_function(self, root):
        function_name = root.name
        args_name = root.arg_list_name
        # its really important to initalize the function outside of its bodys scope
        #
        self.initalize_var(function_name, FunctionType(value=root.body))

        self.func_depth += 1
        self.scope_stack.append({})
        self.initalize_var(args_name, DynamicType())

        self.walk_block(root.body)
        self.scope_stack.pop()
        self.func_depth -= 1
        
    def walk_block(self, root):
        # A block just walks its children in the current scope

        for construct in root.block:
            self.walk_construct(construct)
    
    def walk_if(self, root):

        self.walk_expression(root.condition.root_expr)
        self.scope_stack.append({})
        self.walk_block(root.body)
        self.scope_stack.pop()

        for elif_root in root.elif_branch.block:
            self.walk_elif(elif_root)
        for else_root in root.else_branch.block:
            self.walk_else(else_root)
    
    def walk_elif(self, root):

        self.walk_expression(root.condition.root_expr)
        self.scope_stack.append({})
        self.walk_block(root.body)
        self.scope_stack.pop()
    
    def walk_else(self, root):
        self.scope_stack.append({})
        self.walk_block(root.body)
        self.scope_stack.pop()
    
    
    def walk_for(self, root):
        self.loop_depth += 1
        self.scope_stack.append({})
        left_hand_name = root.variable.value
        right_hand_type = DynamicType()
        if type(right_hand_type) in {NoneType}:
            raise SemanticError(self.file, "For loop bound must be an array, identifier, or number", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end)
        self.initalize_var(left_hand_name, right_hand_type)
        self.walk_block(root.body)
        self.scope_stack.pop()
        self.loop_depth -= 1
    
    
    def walk_while(self, root):
        self.loop_depth += 1
        self.walk_expression(root.condition.root_expr)
        self.walk_block(root.body)
        self.loop_depth -= 1

    def walk_break(self, root):
        if self.loop_depth == 0:
            raise SemanticError(self.file, "cannot break outside of loop scope", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end)
    
    def walk_continue(self, root):
        if self.loop_depth == 0:
            raise SemanticError(self.file, "cannot continue outside of loop scope", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end)
    
    def walk_return(self, root):
        if not self.func_depth:
            raise SemanticError(self.file, "cannot return outside of function scope", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end)
        if root.expression:
            self.walk_expression(root.expression.root_expr)


    # every time a var is assigned we throw it into our current scope
    # to let expressions which use the var in the future know that exists in the current scope
    # with each initalized var being associated with its respective type 
    def initalize_var(self, left_hand, right_hand):

        self.scope_stack[-1][left_hand] = right_hand
    
    def search_for_var(self, name):

        if type(name) == IdentifierNode:
            name = name.value
            
        for scope in reversed(self.scope_stack):
            if name in scope:
                return scope[name]
        return ""
        


    def walk_assignments(self, root):
        
        def walk_assignment_typical(left_hand, op_type, right_hand):
            left_hand_name = left_hand.value
            if op_type in self.ARITH_ASSIGNMENTS and type(right_hand) != DynamicType:
                op_type = self.assignment_to_normal[op_type]
                left_hand_type = self.search_for_var(left_hand_name)
                if not left_hand_type:
                    raise SemanticError(self.file, "variable not initialized", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end)
                # is it the same type?
                if (not ((type(right_hand) in [NumberType, BoolType] and type(left_hand_type) in [NumberType, BoolType]) or type(left_hand_type) == type(right_hand))):
                    # does it adhere to different type operation rules?
                    if (type(left_hand_type), type(right_hand), op_type) not in self.BIN_OP_DIFFERENT_RULES:
                        raise SemanticError(self.file, "Invalid operation", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end)
            self.initalize_var(left_hand_name, right_hand)

        def walk_assignment_index(left_hand, op_type, right_hand):
            left_hand_type = self.walk_expression(left_hand)
            if left_hand_type != DynamicType and right_hand != DynamicType:
                if not left_hand_type:
                    raise SemanticError(self.file, "variable not initialized", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end)
                if op_type in self.ARITH_ASSIGNMENTS:
                    op_type = self.assignment_to_normal[op_type]
                    if (not ((type(right_hand) in [NumberType, BoolType] and type(left_hand_type) in [NumberType, BoolType]) or type(left_hand_type) == type(right_hand))):
                        if (type(left_hand_type), type(right_hand), op_type) not in self.BIN_OP_DIFFERENT_RULES:
                            raise SemanticError(self.file, "Invalid operation", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end)
        
        def walk_assignment_multi(left_hand, op_type, right_hand):
            if type(right_hand) != DynamicType:
                if type(right_hand) != ArrayType:
                    raise SemanticError(self.file, "multi-initialization requires right hand to be dynamic type or static array type", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end)
                if len(left_hand.elements) > len(right_hand.value):
                    raise SemanticError(self.file, "multi-initialization requires right hand length to be equal to or greater than left hand length", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end)
                
                rhs_types = right_hand.value if type(right_hand) == ArrayType else \
                    [DynamicType()] * len(left_hand.elements)
                
                dispatch = {
                IdentifierNode:   walk_assignment_typical,
                IndexNode:        walk_assignment_index,
                ArrayLiteralNode: walk_assignment_multi,   # nested destructuring
            }
                
                for i, n in enumerate(left_hand.elements):
                    left_hand_node = n.root_expr
                    rhs_type  = rhs_types[i] if i < len(rhs_types) else DynamicType()
                    dispatch[type(left_hand_node)](left_hand_node, op_type, rhs_type)
                
        find_assignment_type = {
            IdentifierNode: walk_assignment_typical,
            IndexNode: walk_assignment_index,
            ArrayLiteralNode: walk_assignment_multi,
        }

        find_assignment_type[type(root.left_hand)](root.left_hand, root.op, self.walk_expression(root.right_hand.root_expr))
        
    def walk_expression(self, root):
        
        if type(root) in self.literals:
            actual_type = self.literals[type(root)]
            return actual_type(root.value)
        
        if type(root) == DynamicType:
            return DynamicType()
        
        elif type(root) == BinOpNode:
            op = root.op
            left = self.walk_expression(root.left)
            right = self.walk_expression(root.right)
            

            if type(left) == DynamicType or type(right) == DynamicType:
                return DynamicType()
            
            if (not ((type(right) in [NumberType, BoolType] and type(left) in [NumberType, BoolType]) or type(left) == type(right))) and op in self.ARITH_OPS:
                if (type(left), type(right), op) not in self.BIN_OP_DIFFERENT_RULES:
                    raise SemanticError(self.file, "Invalid operation", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end)
                else:
                    return self.BIN_OP_DIFFERENT_RULES[(type(left), type(right), op)](value=None)
            
            # the value is none because we aren't evaluating anything just determining its type
            # anythingt that requires binop to be evaluated to throw an error will be a runtime error
            if (type(left), type(right), op) not in self.BOOL_OP_RULES:
                if op == TokenType.T_IN:
                    raise SemanticError(self.file, f"in operator not supported between {type(left)} and {type(right)}", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end)
                
            cls = type(left) if op in self.ARITH_OPS else BoolType
            return cls(value=None)
        
        elif type(root) == UnaryOPNode:

            op = self.walk_expression(root.operand)

            if type(op) == DynamicType:
                return DynamicType()
            
            if type(op) not in self.allowed_unary_ops and root.op != TokenType.T_NEGATE:
                raise SemanticError(self.file, "Invalid operation", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end)
            
            # the value is none because we aren't evaluating anything just determining its type
            # anythingt that requires binop to be evaluated to throw an error will be a runtime error
            return BoolType(value=None) if root.op == TokenType.T_NEGATE else NumberType(value=None)
        
        elif type(root) == ArrayLiteralNode:

            checking_exprs = []
            for e in root.elements:
                typed_expression = self.walk_expression(e.root_expr) if type(e) == ExpressionNode else self.walk_expression(e)
                checking_exprs.append(typed_expression)

            return ArrayType(value=checking_exprs)

        elif type(root) == IndexNode:

            base = self.walk_expression(root.base)
            if type(base) == DynamicType:
                return DynamicType()
            # notice the if base.value
            # remember that if it dosent have a value its not staically knowable
            # so we only throw an error ifs its knowable and an error
            # things that are errors after evaluation will be runtime errors

            # pretty sure from here down there is some redundant code but it is only redundant, and working
            if base.value:
                if type(base) not in [ArrayType, StringType]:
                    raise SemanticError(self.file, f"object of {type(base)} not indexable", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end)

            indexes = []

            for idx in root.index:
                idx_type = self.walk_expression(idx.root_expr)
                if type(idx_type) not in [NumberType, BoolType, DynamicType]:
                    raise SemanticError(self.file, "Index must be number", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end)
                indexes.append(idx_type)
            
            # if the base is unknowable statically than their is no point
            # to run over static indexes because we dont know the bounds of the base
            if not base.value:
                return base
            
            for pos, idx in enumerate(indexes):
                
                if type(base) not in [ArrayType, StringType]:
                    raise SemanticError(self.file, "Index out of bounds", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end)
                element_list = base.value

                # if the value is statically unknowable we cant continue iterating
                # through the indexes because we dont know where to nest into
                if idx.value != None:
                    try:
                        base = element_list[idx.value]
                    except IndexError:
                        raise SemanticError(self.file, "Index out of bounds", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end)
                else:
                    break
            
            return base
        
        elif type(root) == IdentifierNode:
            # making sure each identifier is defined if its used in a given scope
            actual_type = self.search_for_var(root.value)
            if not actual_type:
                raise SemanticError(self.file, f"variable not initalized '{root.value}'", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end,)
            return actual_type
            
        elif type(root) == CallNode:
            if type(root.name) != IdentifierNode:
                return DynamicType()
            callee_type = self.search_for_var(root.name)
            if not callee_type:
                raise SemanticError(self.file, f"function not intialized '{root.name}'", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end,)
            if type(callee_type) != FunctionType:
                raise SemanticError(self.file, f"attempt to call non-function '{root.name}'", root.meta_data.line, root.meta_data.column_start, root.meta_data.column_end,)

            # Analyse each argument expression normally.
            for arg in root.args:
                self.walk_expression(arg.root_expr)
            
            return DynamicType()
    



        









