# after this pass, all of the user code will be interpreted through python.
# the user code will be evaluated until a runtime
# error or until the end of the code
# all we are doing here is simulating until one of these things happen

# this file shares many simalarities with our semantic
# analyzer because in both we're essentially just
# tree-walking; in the semantic analyzer we are tree
# walking for types, and in this we are tree walking for runtime values
import operator
from copy import deepcopy

from bang.lexing.lexer import TokenType
from bang.parsing.parser_nodes import (
    ArrayLiteralNode,
    AssignmentNode,
    BinOpNode,
    BlockNode,
    BooleanLiteralNode,
    BreakNode,
    CallNode,
    ContinueNode,
    ExpressionNode,
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
from bang.runtime.evaluator_nodes import (
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
# need to propogate this across potentially every function
# we have; so instead of returning
# "break_signal" and adding custom
# logic to each one, which increases the complexity and
# decreases readability, we create
# private exceptions that allow us to control exactly where each signal
# propogates to


class _ReturnSignal(Exception):
    __slots__ = ("value",)

    def __init__(self, value):
        self.value = value  # carry the result


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

        # remember args is potentially a list of lists

        def _built_in_print(args, meta_data):
            print(*args)

        def _built_in_len(args, meta_data):
            # changet this len args != 1 to accomodate any number of expected arguments
            if len(args) != 1:
                raise EvaluatorError(
                    self.file,
                    "len expects exactly one arg",
                    meta_data.line,
                    meta_data.column_start,
                    meta_data.column_end,
                )
            if not hasattr(args[0], "__len__"):
                raise EvaluatorError(
                    self.file,
                    f"len expects list, str, not {type(args[0])}",
                    meta_data.line,
                    meta_data.column_start,
                    meta_data.column_end,
                )
            return len(args[0])

        def _built_in_sum(args, meta_data):
            if len(args) != 1:
                raise EvaluatorError(
                    self.file,
                    "sum function expects one arg",
                    meta_data.line,
                    meta_data.column_start,
                    meta_data.column_end,
                )
            if type(args[0]) in [str, list]:
                args = args[0]
            else:
                return args[0]

            expected_type = type(args[0])
            if expected_type is int:
                base = 0
            elif expected_type is str:
                base = ""
            elif expected_type is list:
                base = []
            elif expected_type is set:
                base = set()
            elif expected_type is dict:
                base = {}

            for i in args:
                if type(i) is not expected_type:
                    raise EvaluatorError(
                        self.file,
                        "sum function expects argument list of homegenous type",
                        meta_data.line,
                        meta_data.column_start,
                        meta_data.column_end,
                    )
                if type(i) in [set, dict]:
                    base |= i
                else:
                    base += i
            return base

        def _built_in_min(args, meta_data):
            if len(args) != 1:
                raise EvaluatorError(
                    self.file,
                    "min function expects one arg",
                    meta_data.line,
                    meta_data.column_start,
                    meta_data.column_end,
                )
            if type(args[0]) in [str, list]:
                args = args[0]
            else:
                return args[0]
            expected_type = type(args[0])
            base = args[0]
            for i in args:
                if type(i) is not expected_type:
                    raise EvaluatorError(
                        self.file,
                        "min function expects argument list of homegenous type",
                        meta_data.line,
                        meta_data.column_start,
                        meta_data.column_end,
                    )
                try:
                    base = min(base, i)
                except TypeError:
                    raise EvaluatorError(
                        self.file,
                        f"comparison not supported between type {type(base)} and {type(i)}",
                        meta_data.line,
                        meta_data.column_start,
                        meta_data.column_end,
                    ) from None
            return base

        def _built_in_max(args, meta_data):
            if len(args) != 1:
                raise EvaluatorError(
                    self.file,
                    "max function expects one arg",
                    meta_data.line,
                    meta_data.column_start,
                    meta_data.column_end,
                )
            if type(args[0]) in [str, list]:
                args = args[0]
            else:
                return args[0]
            expected_type = type(args[0])
            base = args[0]
            for i in args:
                if type(i) is not expected_type:
                    raise EvaluatorError(
                        self.file,
                        "max function expects argument list of homegenous type",
                        meta_data.line,
                        meta_data.column_start,
                        meta_data.column_end,
                    )
                try:
                    base = max(base, i)
                except TypeError:
                    raise EvaluatorError(
                        self.file,
                        f"comparison not supported between type {type(base)} and {type(i)}",
                        meta_data.line,
                        meta_data.column_start,
                        meta_data.column_end,
                    ) from None
            return base

        def _built_in_sort(args, meta_data):
            if len(args) != 1:
                raise EvaluatorError(
                    self.file,
                    "sort function expects one arg",
                    meta_data.line,
                    meta_data.column_start,
                    meta_data.column_end,
                )
            if type(args[0]) in [str, list]:
                args = args[0]
            else:
                return args[0]
            try:
                return sorted(args)
            except TypeError:
                raise EvaluatorError(
                    self.file,
                    "sort function expects argument list of homogenous, sortable type",
                    meta_data.line,
                    meta_data.column_start,
                    meta_data.column_end,
                ) from None

        def _built_in_set(args, meta_data):
            if not args:
                return set()
            if len(args) != 1:
                raise EvaluatorError(
                    self.file,
                    "set function expects one argument",
                    meta_data.line,
                    meta_data.column_start,
                    meta_data.column_end,
                ) from None
            if type(args[0]) is not list:
                raise EvaluatorError(
                    self.file,
                    "set function expects iterable type as argument",
                    meta_data.line,
                    meta_data.column_start,
                    meta_data.column_end,
                ) from None

            args = args[0]

            try:
                return set(args)
            except TypeError:
                raise EvaluatorError(
                    self.file,
                    "set expects hashable types only",
                    meta_data.line,
                    meta_data.column_start,
                    meta_data.column_end,
                ) from None

        def _built_in_dict(args, meta_data):
            expected_return = {}
            # if empty initialization
            if not args:
                return {}

            # if dict{1,2}
            if len(args) == 2:
                try:
                    return {args[0]: args[1]}
                except TypeError:
                    raise EvaluatorError(
                        self.file,
                        "dict initalization expects key to be hashable",
                        meta_data.line,
                        meta_data.column_start,
                        meta_data.column_end,
                    ) from None

            # if dict{[[1,2], [3,4], [5,6]]}
            if len(args) != 1 or type(args[0]) is not list:
                raise EvaluatorError(
                    self.file,
                    "multi-key dict initalization expects list of lists of length two",
                    meta_data.line,
                    meta_data.column_start,
                    meta_data.column_end,
                )
            for key_val_list in args[0]:
                if (type(key_val_list) is not list) or len(key_val_list) != 2:
                    raise EvaluatorError(
                        self.file,
                        "multi-key dict initalization expects list of lists of length two",
                        meta_data.line,
                        meta_data.column_start,
                        meta_data.column_end,
                    )
                try:
                    expected_return[key_val_list[0]] = key_val_list[1]
                except TypeError:
                    raise EvaluatorError(
                        self.file,
                        "dict initalization expects key to be hashable",
                        meta_data.line,
                        meta_data.column_start,
                        meta_data.column_end,
                    ) from None

            return expected_return

        def _built_in_range(args, meta_data):
            if not args:
                return []

            if len(args) == 1 and type(args[0]) is list:
                args = args[0]

            if len(args) > 3:
                raise EvaluatorError(
                    self.file,
                    "range function expects three args only",
                    meta_data.line,
                    meta_data.column_start,
                    meta_data.column_end,
                )

            if len(args) == 1:
                start = 0
                end = args[0]
                jmp = 1
            elif len(args) == 2:
                start = args[0]
                end = args[1]
                jmp = 1
            elif len(args) == 3:
                start = args[0]
                end = args[1]
                jmp = args[2]

            if jmp == 0:
                raise EvaluatorError(
                    self.file,
                    "jump arg (arg 3) can't be zero due to infinite evaluation",
                    meta_data.line,
                    meta_data.column_start,
                    meta_data.column_end,
                )
            if any(not isinstance(x, (int)) for x in (start, end, jmp)):
                raise EvaluatorError(
                    self.file,
                    "start, jump, and end arguments must be int type",
                    meta_data.line,
                    meta_data.column_start,
                    meta_data.column_end,
                )

            return [i for i in range(start, end, jmp)]

        # by name
        self.built_in_functions = {
            "print": _built_in_print,
            "len": _built_in_len,
            "sum": _built_in_sum,
            "min": _built_in_min,
            "max": _built_in_max,
            "sort": _built_in_sort,
            "set": _built_in_set,
            "dict": _built_in_dict,
            "range": _built_in_range,
        }

        self.built_in_function_objects = set(
            [obj for obj in self.built_in_functions.values()]
        )

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
            NoneLiteralNode: lambda _: 0,
        }

        self.ARITH_OPS = {
            TokenType.T_PLUS,
            TokenType.T_MINUS,
            TokenType.T_ASTERISK,
            TokenType.T_SLASH,
            TokenType.T_DSLASH,
            TokenType.T_EXPO,
        }

        self.ARITH_ASSIGNMENTS = {
            TokenType.T_PLUS_ASSIGN,
            TokenType.T_MINUS_ASSIGN,
            TokenType.T_SLASH_ASSIGN,
            TokenType.T_ASTERISK_ASSIGN,
        }

        self.allowed_unary_ops = {
            int,
        }

        self.construct_to_eval = {
            AssignmentNode: self.eval_assignments,
            IFNode: self.eval_if,
            ForNode: self.eval_for,
            WhileNode: self.eval_while,
            BlockNode: self.eval_block,
            BreakNode: self.eval_break,
            ContinueNode: self.eval_continue,
            ReturnNode: self.eval_return,
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
        # with this, were limiting the number of frames on the scope stack at function creation
        # but were not limiting the contents of those frames.
        # so, we're saying, if this function was declared on the
        # 7th scope, this function can only see the seven scopes
        # (no new scopes the function can see)
        # but we can add infinitely many new variables to those frozen
        # scopes (because we want the function to be able to, say, call itself)
        closure = self.scope_stack[:]

        self.initalize_var(
            function_name,
            runtime_function(body=root.body, params_name=args_name, closure=closure),
        )

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

    def eval_for(self, root):
        self.loop_depth += 1
        self.scope_stack.append({})
        left_hand_name = root.variable.value
        right_hand_val = self.eval_expression(root.bound.root_expr)

        if type(right_hand_val) is int:
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
            except TypeError:
                raise EvaluatorError(
                    self.file,
                    "bound not iterable",
                    root.meta_data.line,
                    root.meta_data.column_start,
                    root.meta_data.column_end,
                ) from None

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
            raise EvaluatorError(
                self.file,
                "cannot break outside of loop scope",
                root.meta_data.line,
                root.meta_data.column_start,
                root.meta_data.column_end,
            )
        raise _BreakSignal()

    def eval_continue(self, root):
        if self.loop_depth == 0:
            raise EvaluatorError(
                self.file,
                "cannot continue outside of loop scope",
                root.meta_data.line,
                root.meta_data.column_start,
                root.meta_data.column_end,
            )
        raise _ContinueSignal()

    def eval_return(self, root):
        if not self.func_depth:
            raise EvaluatorError(
                self.file,
                "cannot return outside of function scope",
                root.meta_data.line,
                root.meta_data.column_start,
                root.meta_data.column_end,
            )
        value = self.eval_expression(root.expression.root_expr)
        raise _ReturnSignal(value=value)

    # every time a var is assigned we throw it into our current scope
    # to let expressions which use the var in the future know that exists in the current scope
    # with each initalized var being associated with its respective type
    def initalize_var(self, left_hand, right_hand):
        self.scope_stack[-1][left_hand] = right_hand

    def search_for_var(self, name, potential_error):
        for idx, scope in enumerate(reversed(self.scope_stack)):
            if name in scope:
                # converts reversed index to normal index
                return len(self.scope_stack) - idx - 1
        raise EvaluatorError(
            self.file,
            f"Variable {name} not found in current scope",
            potential_error.line,
            potential_error.column_start,
            potential_error.column_end,
        )

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

        def eval_assignment_typical(left_hand, right_hand_value):
            left_hand_name = left_hand.value
            try:
                idx = self.search_for_var(left_hand_name, root.meta_data)
                self.scope_stack[idx][left_hand_name] = right_hand_value
            except EvaluatorError:
                self.initalize_var(left_hand_name, right_hand_value)

        def eval_assignment_index(left_hand, right_hand_value):
            if type(left_hand.base) is IdentifierNode:
                base_location = self.search_for_var(
                    left_hand.base.value, root.meta_data
                )
                base_frame = self.scope_stack[base_location]
                target = base_frame[left_hand.base.value]
            else:
                target = self.eval_expression(left_hand.base)
            for idx in left_hand.index[:-1]:
                try:
                    target = target[self.eval_expression(idx.root_expr)]
                except (IndexError, TypeError, KeyError):
                    raise EvaluatorError(
                        self.file,
                        "Index out of bounds",
                        root.meta_data.line,
                        root.meta_data.column_start,
                        root.meta_data.column_end,
                    ) from None
            try:
                final_idx = self.eval_expression(left_hand.index[-1].root_expr)
                target[final_idx] = right_hand_value
            except (IndexError, TypeError, KeyError):
                raise EvaluatorError(
                    self.file,
                    "Index out of bounds",
                    root.meta_data.line,
                    root.meta_data.column_start,
                    root.meta_data.column_end,
                ) from None

        def eval_assignment_multi(left_hand, right_hand_value):
            if type(right_hand_value) not in [list, ArrayLiteralNode]:
                raise EvaluatorError(
                    self.file,
                    "multi-variable assignment right hand must be type list",
                    root.meta_data.line,
                    root.meta_data.column_start,
                    root.meta_data.column_end,
                )
            if len(left_hand.elements) > len(right_hand_value):
                raise EvaluatorError(
                    self.file,
                    "not enough values to unpack",
                    root.meta_data.line,
                    root.meta_data.column_start,
                    root.meta_data.column_end,
                )

            dispatch = {
                IdentifierNode: eval_assignment_typical,
                IndexNode: eval_assignment_index,
                ArrayLiteralNode: eval_assignment_multi,  # nested
            }

            for i, n in enumerate(left_hand.elements):
                left_hand_side = n.root_expr
                assignee = right_hand_value[i]
                if (
                    op_type != TokenType.T_ASSIGN
                    and type(left_hand_side) is not ArrayLiteralNode
                ):
                    assignee = self.eval_bin_ops(
                        BinOpNode(
                            left=left_hand_side,
                            op=assignment_to_normal_ops[op_type],
                            right=assignee,
                            meta_data=root.meta_data,
                        )
                    )
                dispatch[type(left_hand_side)](
                    left_hand=left_hand_side, right_hand_value=assignee
                )

        right_hand_value = self.eval_expression(root.right_hand.root_expr)
        op_type = root.op

        if (
            op_type != TokenType.T_ASSIGN
            and type(root.left_hand) is not ArrayLiteralNode
        ):
            right_hand_value = self.eval_expression(
                BinOpNode(
                    left=root.left_hand,
                    op=assignment_to_normal_ops[op_type],
                    right=root.right_hand.root_expr,
                    meta_data=root.meta_data,
                )
            )

        find_assignment_type = {
            IdentifierNode: eval_assignment_typical,
            IndexNode: eval_assignment_index,
            ArrayLiteralNode: eval_assignment_multi,
        }

        find_assignment_type[type(root.left_hand)](
            left_hand=root.left_hand, right_hand_value=right_hand_value
        )

    # this function handles all expression level contructs such as literals, binary ops,
    # unary ops, and function calls
    def eval_expression(self, root):
        if type(root) in [int, bool, str, float, list, set, dict]:
            return root

        if type(root) is ExpressionNode:
            root = root.root_expr

        if type(root) in self.literals:
            # converting bang literals to python literals
            actual_value_function = self.literals[type(root)]
            return actual_value_function(root.value)

        elif type(root) is BinOpNode:
            # converting bang binary operation into a python literal

            return self.eval_bin_ops(root)

        elif type(root) is UnaryOPNode:
            # converting bang unary operation into a python literal
            return self.eval_unary_ops(root)

        elif type(root) is ArrayLiteralNode:
            # converting bang list into python list of python literals
            return [self.eval_expression(i.root_expr) for i in root.elements]

        elif type(root) is IndexNode:
            # converting bang index into python literal
            index_chain = [self.eval_expression(i.root_expr) for i in root.index]
            base = self.eval_expression(root.base)
            for i in index_chain:
                try:
                    base = base[i]
                except (IndexError, TypeError, KeyError):
                    raise EvaluatorError(
                        self.file,
                        "Index out of bounds",
                        root.meta_data.line,
                        root.meta_data.column_start,
                        root.meta_data.column_end,
                    ) from None
            return base

        elif type(root) is IdentifierNode:
            # converting every bang identifier into a python literal
            return self.scope_stack[self.search_for_var(root.value, root.meta_data)][
                root.value
            ]

        elif type(root) is CallNode:
            # executing a bang block

            if type(root.name) is IdentifierNode:
                func_name = root.name.value
                callee = self.scope_stack[
                    self.search_for_var(func_name, root.meta_data)
                ][func_name]
            else:
                func_name = None
                callee = self.eval_expression(root.name)

            arg_vals = [self.eval_expression(i.root_expr) for i in root.args]

            if type(callee) is runtime_function:
                return self.eval_call(callee, arg_vals, root.meta_data)

            if func_name in self.built_in_functions:
                return self.built_in_functions[func_name](arg_vals, root.meta_data)

            # this is required because, for ex., callee the case of bar{}{1,2},
            # where bar returns a function signature, is a raw function object
            if callee in self.built_in_function_objects:
                return callee(arg_vals, root.meta_data)

            raise EvaluatorError(
                self.file,
                f"'{root.name}' is not callable",
                root.meta_data.line,
                root.meta_data.column_start,
                root.meta_data.column_end,
            )

    # -------------------------------------------
    # BINARY OPERATIONS START
    # -------------------------------------------

    def eval_bin_ops(self, root):
        op = root.op

        left = self.eval_expression(root.left)
        right = self.eval_expression(root.right)

        # -------------------------------------------
        # INT OPERATIONS START
        # -------------------------------------------

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
                TokenType.T_AND: lambda a, b: a and b,
                TokenType.T_OR: lambda a, b: a or b,
            }

            if op in (TokenType.T_SLASH, TokenType.T_DSLASH) and right == 0:
                raise EvaluatorError(
                    self.file,
                    "division by zero",
                    root.meta_data.line,
                    root.meta_data.column_start,
                    root.meta_data.column_end,
                )

            if op not in supported_types:
                raise EvaluatorError(
                    self.file,
                    f"operation '{op}' not supported between {type(left)} and {type(right)}",
                    root.meta_data.line,
                    root.meta_data.column_start,
                    root.meta_data.column_end,
                )

            return supported_types[op](left, right)

        # -------------------------------------------
        # INT OPERATIONS END
        # -------------------------------------------

        # -------------------------------------------
        # STRING OPERATIONS START
        # -------------------------------------------

        def eval_str_bin_op(left, op, right):
            def str_sub(a, b):
                return a.replace(b, "")

            def str_div(a, b):
                if b == "":
                    return list(a)
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
                TokenType.T_AND: lambda a, b: a and b,
                TokenType.T_OR: lambda a, b: a or b,
                TokenType.T_IN: lambda a, b: a in b,
            }

            if op not in supported_types:
                raise EvaluatorError(
                    self.file,
                    f"operation '{op}' not supported between {type(left)} and {type(right)}",
                    root.meta_data.line,
                    root.meta_data.column_start,
                    root.meta_data.column_end,
                )

            return supported_types[op](left, right)

        # -------------------------------------------
        # STRING OPERATIONS END
        # -------------------------------------------

        # -------------------------------------------
        # LIST OPERATIONS START
        # -------------------------------------------

        def eval_list_bin_op(left, op, right):
            def list_div_helper(a, b, div_type):
                if b == 0:
                    raise EvaluatorError(
                        self.file,
                        "attempted divison by zero",
                        root.meta_data.line,
                        root.meta_data.column_start,
                        root.meta_data.column_end,
                    )
                return a / b if div_type == "true" else a // b

            def list_sub(a, b):
                to_remove = set(b)
                return [x for x in a if x not in to_remove]

            def list_mul(a, b):
                if type(a) is list and type(b) is list:
                    if len(a) != len(b):
                        if 1 not in [len(a), len(b)]:
                            raise EvaluatorError(
                                self.file,
                                "list element-wise multiplication is not "
                                "supported between lists of different lengths where"
                                "multiplicand length is not one",
                                root.meta_data.line,
                                root.meta_data.column_start,
                                root.meta_data.column_end,
                            )
                        multiplier = b[0] if len(b) == 1 else a[0]
                        base = a if len(a) != 1 else b
                        return [x * multiplier for x in base]
                    else:
                        return [i * j for i, j in zip(a, b, strict=False)]
                else:
                    # this will be where operations such as [1] * 3
                    # go which we will need to change semantic pass to allow
                    pass

            def list_div(a, b):
                if type(a) is list and type(b) is list:
                    if len(a) != len(b):
                        if 1 not in [len(a), len(b)]:
                            raise EvaluatorError(
                                self.file,
                                "list element-wise divsion is not supported "
                                "between lists of different lengths where"
                                "divisor length is not one",
                                root.meta_data.line,
                                root.meta_data.column_start,
                                root.meta_data.column_end,
                            )
                        divisor = b[0] if len(b) == 1 else a[0]
                        base = a if len(a) != 1 else b
                        return [list_div_helper(x, divisor, "true") for x in base]
                    else:
                        return [
                            list_div_helper(i, j, "true")
                            for i, j in zip(a, b, strict=False)
                        ]

            def list_floor_div(a, b):
                if type(a) is list and type(b) is list:
                    if len(a) != len(b):
                        if 1 not in [len(a), len(b)]:
                            raise EvaluatorError(
                                self.file,
                                "list element-wise divsion is not supported "
                                "between lists of different lengths where"
                                "divisor length is not one",
                                root.meta_data.line,
                                root.meta_data.column_start,
                                root.meta_data.column_end,
                            )
                        divisor = b[0] if len(b) == 1 else a[0]
                        base = a if len(a) != 1 else b
                        return [list_div_helper(x, divisor, "floor") for x in base]
                    else:
                        return [
                            list_div_helper(i, j, "floor")
                            for i, j in zip(a, b, strict=False)
                        ]

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
                TokenType.T_AND: lambda a, b: a and b,
                TokenType.T_OR: lambda a, b: a or b,
                TokenType.T_IN: lambda a, b: a in b,
            }

            if op not in supported_types:
                raise EvaluatorError(
                    self.file,
                    f"operation '{op}' not supported between {type(left)} and {type(right)}",
                    root.meta_data.line,
                    root.meta_data.column_start,
                    root.meta_data.column_end,
                )
            return supported_types[op](left, right)

        # -------------------------------------------
        # LIST OPERATIONS END
        # -------------------------------------------

        def eval_set_bin_op(left, op, right):
            def set_add(a, b):
                return a | b

            supported_types = {
                TokenType.T_PLUS: set_add,
                TokenType.T_MINUS: operator.sub,
                TokenType.T_LT: operator.lt,
                TokenType.T_LEQ: operator.le,
                TokenType.T_GT: operator.gt,
                TokenType.T_GTEQ: operator.ge,
                TokenType.T_EQ: operator.eq,
                TokenType.T_NEQ: operator.ne,
                TokenType.T_AND: lambda a, b: a and b,
                TokenType.T_OR: lambda a, b: a or b,
            }

            if op not in supported_types:
                raise EvaluatorError(
                    self.file,
                    f"operation '{op}' not supported between {type(left)} and {type(right)}",
                    root.meta_data.line,
                    root.meta_data.column_start,
                    root.meta_data.column_end,
                )
            return supported_types[op](left, right)

        def eval_dict_bin_op(left, op, right):
            def dict_add(a, b):
                return a | b

            def dict_sub(a, b):
                return {k: v for k, v in a.items() if k not in b}

            supported_types = {
                TokenType.T_PLUS: dict_add,
                TokenType.T_MINUS: dict_sub,
                TokenType.T_EQ: operator.eq,
                TokenType.T_NEQ: operator.ne,
                TokenType.T_AND: lambda a, b: a and b,
                TokenType.T_OR: lambda a, b: a or b,
            }

            if op not in supported_types:
                raise EvaluatorError(
                    self.file,
                    f"operation '{op}' not supported between {type(left)} and {type(right)}",
                    root.meta_data.line,
                    root.meta_data.column_start,
                    root.meta_data.column_end,
                )
            return supported_types[op](left, right)

        def eval_different_bin_op(left, op, right):
            def eval_different_in(a, b):
                try:
                    return a in b
                except TypeError:
                    raise EvaluatorError(
                        self.file,
                        f"in binary operation not supported between {type(a)} and {type(b)}",
                        root.meta_data.line,
                        root.meta_data.column_start,
                        root.meta_data.column_end,
                    ) from None

            supported_types = {
                (list, int, TokenType.T_ASTERISK): lambda a, b: [
                    deepcopy(i) for i in a for _ in range(b)
                ],
                (int, list, TokenType.T_ASTERISK): lambda a, b: [
                    deepcopy(i) for i in b for _ in range(a)
                ],
                (str, int, TokenType.T_ASTERISK): operator.mul,
                (int, str, TokenType.T_ASTERISK): operator.mul,
                TokenType.T_EQ: operator.eq,
                TokenType.T_NEQ: operator.ne,
                TokenType.T_AND: lambda a, b: a and b,
                TokenType.T_OR: lambda a, b: a or b,
                TokenType.T_IN: eval_different_in,
            }

            if (
                op not in supported_types
                and (type(left), type(right), op) not in supported_types
            ):
                raise EvaluatorError(
                    self.file,
                    f"operation '{op}' not supported between {type(left)} and {type(right)}",
                    root.meta_data.line,
                    root.meta_data.column_start,
                    root.meta_data.column_end,
                )

            return (
                supported_types[op](left, right)
                if op in supported_types
                else supported_types[(type(left), type(right), op)](left, right)
            )

        type_dispatch = {
            int: eval_int_bin_op,
            float: eval_int_bin_op,
            bool: eval_int_bin_op,
            str: eval_str_bin_op,
            list: eval_list_bin_op,
            set: eval_set_bin_op,
            dict: eval_dict_bin_op,
        }
        same_type = [int, float, bool]
        dispatcher = eval_different_bin_op
        if type(left) is type(right) or (
            type(left) in same_type and type(right) in same_type
        ):
            dispatcher = type_dispatch.get(type(left))

        return dispatcher(left, op, right)

    # -------------------------------------------
    # BINARY OPERATIONS END
    # -------------------------------------------

    # -------------------------------------------
    # UNARY OPERATIONS START
    # -------------------------------------------

    def eval_unary_ops(self, root):
        # since each unary operation is pretty clear on what it does
        # we will dispatch based on unary operator not type

        def eval_negate(operand):
            return not operand

        def eval_uminus(operand):
            if type(operand) in [int, float]:
                return -operand
            raise EvaluatorError(
                self.file,
                f"unary negation not supported on type {type(operand)}",
                root.meta_data.line,
                root.meta_data.column_start,
                root.meta_data.column_end,
            )

        def eval_uplus(operand):
            if type(operand) in [int, float]:
                return +operand
            raise EvaluatorError(
                self.file,
                f"unary plus not supported on type {type(operand)}",
                root.meta_data.line,
                root.meta_data.column_start,
                root.meta_data.column_end,
            )

        operator_dispatch = {
            TokenType.T_NEGATE: eval_negate,
            TokenType.T_UMINUS: eval_uminus,
            TokenType.T_UPLUS: eval_uplus,
        }
        operator = root.op
        operand = self.eval_expression(root.operand)
        return operator_dispatch[operator](operand)

    # -------------------------------------------
    # UNARY OPERATIONS END
    # -------------------------------------------

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
