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
)
from bang.parsing.parser_nodes import (
    ARRAY_LITERAL_NODE_CLASS,
    ASSIGNMENT_NODE_CLASS,
    BIN_OP_NODE_CLASS,
    BLOCK_NODE_CLASS,
    BOOLEAN_LITERAL_NODE_CLASS,
    BREAK_NODE_CLASS,
    CALL_NODE_CLASS,
    CONTINUE_NODE_CLASS,
    DATA_CLASS_NODE_CLASS,
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
from bang.runtime.evaluator_nodes import (
    RUN_TIME_DATACLASS,
    RUN_TIME_FUNCTION,
    RUN_TIME_INSTANCE,
)


class EvaluatorError(Exception):
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
        crt_length = self.end - self.start if self.end - self.start != 0 else 1
        pointers = " " * (self.start - 1) + "^" * crt_length
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
    T_PLUS_ASSIGN_ENUM_VAL = T_PLUS_ASSIGN_ENUM_VAL
    T_MINUS_ASSIGN_ENUM_VAL = T_MINUS_ASSIGN_ENUM_VAL
    T_ASTERISK_ASSIGN_ENUM_VAL = T_ASTERISK_ASSIGN_ENUM_VAL
    T_SLASH_ASSIGN_ENUM_VAL = T_SLASH_ASSIGN_ENUM_VAL

    T_EQ_ENUM_VAL = T_EQ_ENUM_VAL
    T_NEQ_ENUM_VAL = T_NEQ_ENUM_VAL
    T_LT_ENUM_VAL = T_LT_ENUM_VAL
    T_LEQ_ENUM_VAL = T_LEQ_ENUM_VAL
    T_GT_ENUM_VAL = T_GT_ENUM_VAL
    T_GTEQ_ENUM_VAL = T_GTEQ_ENUM_VAL
    T_DSLASH_ENUM_VAL = T_DSLASH_ENUM_VAL
    T_EXPO_ENUM_VAL = T_EXPO_ENUM_VAL
    T_AND_ENUM_VAL = T_AND_ENUM_VAL
    T_OR_ENUM_VAL = T_OR_ENUM_VAL

    # Literals
    T_NONE_ENUM_VAL = T_NONE_ENUM_VAL
    T_INT_ENUM_VAL = T_INT_ENUM_VAL
    T_FLOAT_ENUM_VAL = T_FLOAT_ENUM_VAL
    T_BOOL_ENUM_VAL = T_BOOL_ENUM_VAL
    T_STRING_ENUM_VAL = T_STRING_ENUM_VAL
    T_IDENT_ENUM_VAL = T_IDENT_ENUM_VAL

    # Keywords
    T_IF_ENUM_VAL = T_IF_ENUM_VAL
    T_ELIF_ENUM_VAL = T_ELIF_ENUM_VAL
    T_ELSE_ENUM_VAL = T_ELSE_ENUM_VAL
    T_FOR_ENUM_VAL = T_FOR_ENUM_VAL
    T_WHILE_ENUM_VAL = T_WHILE_ENUM_VAL
    T_BREAK_ENUM_VAL = T_BREAK_ENUM_VAL
    T_CONTINUE_ENUM_VAL = T_CONTINUE_ENUM_VAL
    T_RETURN_ENUM_VAL = T_RETURN_ENUM_VAL
    T_END_ENUM_VAL = T_END_ENUM_VAL
    T_FN_ENUM_VAL = T_FN_ENUM_VAL
    T_IN_ENUM_VAL = T_IN_ENUM_VAL
    T_DATA_ENUM_VAL = T_DATA_ENUM_VAL

    ARRAY_LITERAL_NODE_CLASS = ARRAY_LITERAL_NODE_CLASS
    ASSIGNMENT_NODE_CLASS = ASSIGNMENT_NODE_CLASS
    BIN_OP_NODE_CLASS = BIN_OP_NODE_CLASS
    BLOCK_NODE_CLASS = BLOCK_NODE_CLASS
    BOOLEAN_LITERAL_NODE_CLASS = BOOLEAN_LITERAL_NODE_CLASS
    BREAK_NODE_CLASS = BREAK_NODE_CLASS
    CALL_NODE_CLASS = CALL_NODE_CLASS
    CONTINUE_NODE_CLASS = CONTINUE_NODE_CLASS
    DATA_CLASS_NODE_CLASS = DATA_CLASS_NODE_CLASS
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

    RUN_TIME_DATACLASS = RUN_TIME_DATACLASS
    RUN_TIME_FUNCTION = RUN_TIME_FUNCTION
    RUN_TIME_INSTANCE = RUN_TIME_INSTANCE

    LITERALS = {
        INTEGER_LITERAL_NODE_CLASS: int,
        FLOAT_LITERAL_NODE_CLASS: float,
        STRING_LITERAL_NODE_CLASS: str,
        # we will be converting booleans to
        # zeroes and ones respectivley and none to zero
        BOOLEAN_LITERAL_NODE_CLASS: int,
        NONE_LITERAL_NODE_CLASS: lambda _: 0,
    }

    ARITH_OPS = {
        T_PLUS_ENUM_VAL,
        T_MINUS_ENUM_VAL,
        T_ASTERISK_ENUM_VAL,
        T_SLASH_ENUM_VAL,
        T_DSLASH_ENUM_VAL,
        T_EXPO_ENUM_VAL,
    }

    ARITH_ASSIGNMENTS = {
        T_PLUS_ASSIGN_ENUM_VAL,
        T_MINUS_ASSIGN_ENUM_VAL,
        T_SLASH_ASSIGN_ENUM_VAL,
        T_ASTERISK_ASSIGN_ENUM_VAL,
    }

    ALLOWED_UNARY_OPS = {
        int,
    }

    ASSIGNMENT_TO_NORMAL_OPS = {
        T_PLUS_ASSIGN_ENUM_VAL: T_PLUS_ENUM_VAL,
        T_MINUS_ASSIGN_ENUM_VAL: T_MINUS_ENUM_VAL,
        T_SLASH_ASSIGN_ENUM_VAL: T_SLASH_ENUM_VAL,
        T_ASTERISK_ASSIGN_ENUM_VAL: T_ASTERISK_ENUM_VAL,
    }

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
                    f"len expects iterable not {type(args[0])}",
                    meta_data.line,
                    meta_data.column_start,
                    meta_data.column_end,
                )
            return len(args[0])

        def _built_in_sum(args, meta_data):
            if len(args) == 1:
                if type(args[0]) is list:
                    args = args[0]
                elif type(args[0]) is set:
                    args = list(args[0])
                else:
                    return args[0]

            if not args:
                return 0

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
                if type(i) in (set, dict):
                    base |= i
                else:
                    base += i
            return base

        def _built_in_min(args, meta_data):
            if len(args) == 1:
                if type(args[0]) is list:
                    args = args[0]
                elif type(args[0]) is set:
                    args = list(args[0])
                else:
                    return args[0]

            if not args:
                raise EvaluatorError(
                    self.file,
                    "min function expects atleast one arg",
                    meta_data.line,
                    meta_data.column_start,
                    meta_data.column_end,
                )

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
            if len(args) == 1:
                if type(args[0]) is list:
                    args = args[0]
                elif type(args[0]) is set:
                    args = list(args[0])
                else:
                    return args[0]

            if not args:
                raise EvaluatorError(
                    self.file,
                    "max function expects atleast one arg",
                    meta_data.line,
                    meta_data.column_start,
                    meta_data.column_end,
                )

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
            if len(args) == 1:
                if type(args[0]) is list:
                    args = args[0]
                elif type(args[0]) is set:
                    args = list(args[0])
                else:
                    return args[0]

            if not args:
                raise EvaluatorError(
                    self.file,
                    "sort function expects atleast one arg",
                    meta_data.line,
                    meta_data.column_start,
                    meta_data.column_end,
                )

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
            if len(args) == 1:
                if type(args[0]) is list:
                    args = args[0]
                elif type(args[0]) is set:
                    args = list(args[0])

            if not args:
                return set()

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

            if len(args) == 1:
                if type(args[0]) is list:
                    args = args[0]
                elif type(args[0]) is set:
                    args = list(args[0])

            if not args:
                return {}

            for i in range(0, len(args), 2):
                if i + 1 >= len(args):
                    raise EvaluatorError(
                        self.file,
                        "every key must be paired with a value",
                        meta_data.line,
                        meta_data.column_start,
                        meta_data.column_end,
                    )
                try:
                    expected_return[args[i]] = args[i + 1]
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
            if len(args) == 1 and type(args[0]) is list:
                args = args[0]

            if not args:
                return []

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

        self.construct_to_eval = {
            self.ASSIGNMENT_NODE_CLASS: self.eval_assignments,
            self.IF_NODE_CLASS: self.eval_if,
            self.FOR_NODE_CLASS: self.eval_for,
            self.WHILE_NODE_CLASS: self.eval_while,
            self.BLOCK_NODE_CLASS: self.eval_block,
            self.BREAK_NODE_CLASS: self.eval_break,
            self.CONTINUE_NODE_CLASS: self.eval_continue,
            self.RETURN_NODE_CLASS: self.eval_return,
            self.EXPRESSION_NODE_CLASS: self.eval_expression,
            self.FUNCTION_NODE_CLASS: self.eval_function,
            self.CALL_NODE_CLASS: self.eval_expression,
            self.DATA_CLASS_NODE_CLASS: self.eval_dataclass,
        }

        self.built_in_function_objects = set([obj for obj in self.built_in_functions.values()])

        self.scope_stack[0].update(self.built_in_functions)

        # we need to know the loop depth for the break/continue etc constructs
        # because if we see a break outside of a loop for example we can throw an error
        self.loop_depth = 0
        self.func_depth = 0

    def eval_program(self):
        for construct in self.roots:
            self.eval_construct(construct)

    # could probably use this eval_construct more
    # typically but its clearer to just call the specific expression
    # in some cases although this could change
    def eval_construct(self, root):
        handler = self.construct_to_eval.get(type(root))
        return handler(root)

    def eval_dataclass(self, root):
        dataclass_name = root.name
        seen = set()
        dataclass_fields = [f for f in root.fields if not (f in seen or seen.add(f))]
        self.initalize_var(dataclass_name, RUN_TIME_DATACLASS(fields=dataclass_fields))

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
            RUN_TIME_FUNCTION(body=root.body, params_name=args_name, closure=closure),
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
        for depth in range(len(self.scope_stack) - 1, -1, -1):
            scope = self.scope_stack[depth]
            if left_hand in scope:
                scope[left_hand] = right_hand
                return
        # Otherwise define it in the current scope
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

        T_ASSIGN_ENUM_VAL = self.T_ASSIGN_ENUM_VAL
        BIN_OP_NODE_CLASS = self.BIN_OP_NODE_CLASS
        ASSIGNMENT_TO_NORMAL_OPS = self.ASSIGNMENT_TO_NORMAL_OPS

        def eval_assignment_typical(left_hand, right_hand_value):
            left_hand_name = left_hand.value
            try:
                idx = self.search_for_var(left_hand_name, root.meta_data)
                self.scope_stack[idx][left_hand_name] = right_hand_value
            except EvaluatorError:
                self.initalize_var(left_hand_name, right_hand_value)

        def eval_assignment_index(left_hand, right_hand_value):
            left_hand_base = left_hand.base
            if type(left_hand_base) is self.IDENTIFIER_NODE_CLASS:
                base_location = self.search_for_var(left_hand_base.value, root.meta_data)
                base_frame = self.scope_stack[base_location]
                target = base_frame[left_hand.base.value]
            else:
                target = self.eval_expression(left_hand_base)
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

        def eval_assignment_field(left_hand, right_hand_value):
            base = self.eval_expression(left_hand.base)
            chain = left_hand.field

            for name in chain[:-1]:
                if type(base) is not self.RUN_TIME_INSTANCE:
                    raise EvaluatorError(
                        self.file,
                        "field access is only performable on instances of classes",
                        left_hand.meta_data.line,
                        left_hand.meta_data.column_start,
                        left_hand.meta_data.column_end,
                    )
                if name not in base.fields:
                    raise EvaluatorError(
                        self.file,
                        "field name wasn't included in the "
                        "definition of the instance's corresponding class",
                        left_hand.meta_data.line,
                        left_hand.meta_data.column_start,
                        left_hand.meta_data.column_end,
                    )
                base = base.fields[name]

            final_name = chain[-1]

            if type(base) is not self.RUN_TIME_INSTANCE:
                raise EvaluatorError(
                    self.file,
                    "field access is only performable on instances of classes",
                    left_hand.meta_data.line,
                    left_hand.meta_data.column_start,
                    left_hand.meta_data.column_end,
                )
            if final_name not in base.fields:
                raise EvaluatorError(
                    self.file,
                    "field name wasn't included in the definition "
                    "of the instance's corresponding class",
                    left_hand.meta_data.line,
                    left_hand.meta_data.column_start,
                    left_hand.meta_data.column_end,
                )

            base.fields[final_name] = right_hand_value

        def eval_assignment_multi(left_hand, right_hand_value):
            ARRAY_LITERAL_NODE_CLASS = self.ARRAY_LITERAL_NODE_CLASS
            if type(right_hand_value) not in (list, ARRAY_LITERAL_NODE_CLASS):
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

            # try and optimize this. maybe turn nexted funcs into methods

            for i, n in enumerate(left_hand.elements):
                left_hand_side = n.root_expr
                assignee = right_hand_value[i]
                if (
                    op_type_id != T_ASSIGN_ENUM_VAL
                    and type(left_hand_side) is not ARRAY_LITERAL_NODE_CLASS
                ):
                    assignee = self.eval_bin_ops(
                        BIN_OP_NODE_CLASS(
                            left=left_hand_side,
                            op=ASSIGNMENT_TO_NORMAL_OPS[op_type_id],
                            right=assignee,
                            meta_data=root.meta_data,
                        )
                    )
                DISPATCH_ASSIGNMENT_TO_FUNC[type(left_hand_side)](
                    left_hand=left_hand_side, right_hand_value=assignee
                )

        right_hand_value = self.eval_expression(root.right_hand.root_expr)
        op_type_id = root.op
        type_root_left_hand = type(root.left_hand)
        if op_type_id != T_ASSIGN_ENUM_VAL and type_root_left_hand is not ARRAY_LITERAL_NODE_CLASS:
            right_hand_value = self.eval_expression(
                BIN_OP_NODE_CLASS(
                    left=root.left_hand,
                    op=ASSIGNMENT_TO_NORMAL_OPS[op_type_id],
                    right=root.right_hand.root_expr,
                    meta_data=root.meta_data,
                )
            )

        DISPATCH_ASSIGNMENT_TO_FUNC = {
            self.IDENTIFIER_NODE_CLASS: eval_assignment_typical,
            self.INDEX_NODE_CLASS: eval_assignment_index,
            self.ARRAY_LITERAL_NODE_CLASS: eval_assignment_multi,  # nested
            self.FIELD_ACCESS_NODE_CLASS: eval_assignment_field,
        }

        DISPATCH_ASSIGNMENT_TO_FUNC[type_root_left_hand](
            left_hand=root.left_hand, right_hand_value=right_hand_value
        )

    # this function handles all expression level contructs such as literals, binary ops,
    # unary ops, and function calls
    def eval_expression(self, root):
        type_root = type(root)
        if type_root in (int, bool, str, float, list, set, dict):
            return root

        if type_root is self.EXPRESSION_NODE_CLASS:
            root = root.root_expr
            type_root = type(root)

        if type_root in self.LITERALS:
            # converting bang literals to python literals
            actual_value_function = self.LITERALS[type_root]
            return actual_value_function(root.value)

        elif type_root is self.BIN_OP_NODE_CLASS:
            # converting bang binary operation into a python literal

            return self.eval_bin_ops(root)

        elif type_root is self.UNARY_OP_NODE_CLASS:
            # converting bang unary operation into a python literal
            return self.eval_unary_ops(root)

        elif type_root is self.ARRAY_LITERAL_NODE_CLASS:
            # converting bang list into python list of python literals
            return [self.eval_expression(i.root_expr) for i in root.elements]

        elif type_root is self.INDEX_NODE_CLASS:
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

        elif type_root is self.IDENTIFIER_NODE_CLASS:
            # converting every bang identifier into a python literal
            return self.scope_stack[self.search_for_var(root.value, root.meta_data)][root.value]

        elif type_root is self.CALL_NODE_CLASS:
            # executing a bang block

            # calling dynamic value?
            root_name = root.name
            if type(root_name) is self.IDENTIFIER_NODE_CLASS:
                func_name = root.name.value
                callee = self.scope_stack[self.search_for_var(func_name, root.meta_data)][func_name]
            else:
                func_name = None
                callee = self.eval_expression(root_name)

            arg_vals = [self.eval_expression(i.root_expr) for i in root.args]

            # calling dataclass
            type_callee = type(callee)
            if type_callee is self.RUN_TIME_DATACLASS:
                fields = {}
                for idx, field in enumerate(callee.fields):
                    fields[field] = 0
                    if len(root.args) > idx:
                        fields[field] = arg_vals[idx]

                return self.RUN_TIME_INSTANCE(of=root_name.value, fields=fields)

            # calling function value?
            if type_callee is self.RUN_TIME_FUNCTION:
                return self.eval_call(callee, arg_vals, root.meta_data)

            if not callable(callee):
                raise EvaluatorError(
                    self.file,
                    f"attempt to call non-function (type {type_callee})",
                    root.meta_data.line,
                    root.meta_data.column_start,
                    root.meta_data.column_end,
                )

            # has to be last due to dict access throwing error on non-func-name
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

        elif type_root is self.FIELD_ACCESS_NODE_CLASS:
            base = self.eval_expression(root.base)
            for name in root.field:
                if type(base) is not self.RUN_TIME_INSTANCE:
                    raise EvaluatorError(
                        self.file,
                        "field access is only performable on instances of classes",
                        root.meta_data.line,
                        root.meta_data.column_start,
                        root.meta_data.column_end,
                    )
                if name not in base.fields:
                    raise EvaluatorError(
                        self.file,
                        "field name wasn't included in the definition of "
                        "the instance's corresponding class",
                        root.meta_data.line,
                        root.meta_data.column_start,
                        root.meta_data.column_end,
                    )
                base = base.fields[name]
            return base

    # -------------------------------------------
    # BINARY OPERATIONS START
    # -------------------------------------------

    def eval_bin_ops(self, root):
        T_PLUS_ENUM_VAL = self.T_PLUS_ENUM_VAL
        T_MINUS_ENUM_VAL = self.T_MINUS_ENUM_VAL
        T_ASTERISK_ENUM_VAL = self.T_ASTERISK_ENUM_VAL
        T_SLASH_ENUM_VAL = self.T_SLASH_ENUM_VAL
        T_DSLASH_ENUM_VAL = self.T_DSLASH_ENUM_VAL
        T_EXPO_ENUM_VAL = self.T_EXPO_ENUM_VAL
        T_EQ_ENUM_VAL = self.T_EQ_ENUM_VAL
        T_NEQ_ENUM_VAL = self.T_NEQ_ENUM_VAL
        T_LT_ENUM_VAL = self.T_LT_ENUM_VAL
        T_LEQ_ENUM_VAL = self.T_LEQ_ENUM_VAL
        T_GT_ENUM_VAL = self.T_GT_ENUM_VAL
        T_GTEQ_ENUM_VAL = self.T_GTEQ_ENUM_VAL
        T_AND_ENUM_VAL = self.T_AND_ENUM_VAL
        T_OR_ENUM_VAL = self.T_OR_ENUM_VAL
        T_IN_ENUM_VAL = self.T_IN_ENUM_VAL

        op = root.op
        left = self.eval_expression(root.left)
        right = self.eval_expression(root.right)
        type_left = type(left)
        type_right = type(right)

        # -------------------------------------------
        # INT OPERATIONS START
        # -------------------------------------------

        def eval_int_bin_op(left, op_type_id, right):
            # every supported operation between two ints in bang

            supported_types = {
                T_PLUS_ENUM_VAL: operator.add,
                T_MINUS_ENUM_VAL: operator.sub,
                T_ASTERISK_ENUM_VAL: operator.mul,
                T_SLASH_ENUM_VAL: operator.truediv,
                T_DSLASH_ENUM_VAL: operator.floordiv,
                T_EXPO_ENUM_VAL: operator.pow,
                T_EQ_ENUM_VAL: operator.eq,
                T_NEQ_ENUM_VAL: operator.ne,
                T_LT_ENUM_VAL: operator.lt,
                T_LEQ_ENUM_VAL: operator.le,
                T_GT_ENUM_VAL: operator.gt,
                T_GTEQ_ENUM_VAL: operator.ge,
                T_AND_ENUM_VAL: lambda a, b: a and b,
                T_OR_ENUM_VAL: lambda a, b: a or b,
            }

            if op_type_id in (T_SLASH_ENUM_VAL, T_DSLASH_ENUM_VAL) and right == 0:
                raise EvaluatorError(
                    self.file,
                    "division by zero",
                    root.meta_data.line,
                    root.meta_data.column_start,
                    root.meta_data.column_end,
                )

            if op_type_id not in supported_types:
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
                T_PLUS_ENUM_VAL: operator.add,
                T_MINUS_ENUM_VAL: str_sub,
                T_SLASH_ENUM_VAL: str_div,
                T_LT_ENUM_VAL: operator.lt,
                T_LEQ_ENUM_VAL: operator.le,
                T_GT_ENUM_VAL: operator.gt,
                T_GTEQ_ENUM_VAL: operator.ge,
                T_EQ_ENUM_VAL: operator.eq,
                T_NEQ_ENUM_VAL: operator.ne,
                T_AND_ENUM_VAL: lambda a, b: a and b,
                T_OR_ENUM_VAL: lambda a, b: a or b,
                T_IN_ENUM_VAL: lambda a, b: a in b,
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
                        if 1 not in (len(a), len(b)):
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
                        if 1 not in (len(a), len(b)):
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
                        return [list_div_helper(i, j, "true") for i, j in zip(a, b, strict=False)]

            def list_floor_div(a, b):
                if type(a) is list and type(b) is list:
                    if len(a) != len(b):
                        if 1 not in (len(a), len(b)):
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
                        return [list_div_helper(i, j, "floor") for i, j in zip(a, b, strict=False)]

            supported_types = {
                T_PLUS_ENUM_VAL: operator.add,
                T_MINUS_ENUM_VAL: list_sub,
                T_ASTERISK_ENUM_VAL: list_mul,
                T_SLASH_ENUM_VAL: list_div,
                T_DSLASH_ENUM_VAL: list_floor_div,
                T_LT_ENUM_VAL: operator.lt,
                T_LEQ_ENUM_VAL: operator.le,
                T_GT_ENUM_VAL: operator.gt,
                T_GTEQ_ENUM_VAL: operator.ge,
                T_EQ_ENUM_VAL: operator.eq,
                T_NEQ_ENUM_VAL: operator.ne,
                T_AND_ENUM_VAL: lambda a, b: a and b,
                T_OR_ENUM_VAL: lambda a, b: a or b,
                T_IN_ENUM_VAL: lambda a, b: a in b,
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
                T_PLUS_ENUM_VAL: set_add,
                T_MINUS_ENUM_VAL: operator.sub,
                T_LT_ENUM_VAL: operator.lt,
                T_LEQ_ENUM_VAL: operator.le,
                T_GT_ENUM_VAL: operator.gt,
                T_GTEQ_ENUM_VAL: operator.ge,
                T_EQ_ENUM_VAL: operator.eq,
                T_NEQ_ENUM_VAL: operator.ne,
                T_AND_ENUM_VAL: lambda a, b: a and b,
                T_OR_ENUM_VAL: lambda a, b: a or b,
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
                T_PLUS_ENUM_VAL: dict_add,
                T_MINUS_ENUM_VAL: dict_sub,
                T_EQ_ENUM_VAL: operator.eq,
                T_NEQ_ENUM_VAL: operator.ne,
                T_AND_ENUM_VAL: lambda a, b: a and b,
                T_OR_ENUM_VAL: lambda a, b: a or b,
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
                (list, int, T_ASTERISK_ENUM_VAL): lambda a, b: [
                    deepcopy(i) for i in a for _ in range(b)
                ],
                (int, list, T_ASTERISK_ENUM_VAL): lambda a, b: [
                    deepcopy(i) for i in b for _ in range(a)
                ],
                (str, int, T_ASTERISK_ENUM_VAL): operator.mul,
                (int, str, T_ASTERISK_ENUM_VAL): operator.mul,
                T_EQ_ENUM_VAL: operator.eq,
                T_NEQ_ENUM_VAL: operator.ne,
                T_AND_ENUM_VAL: lambda a, b: a and b,
                T_OR_ENUM_VAL: lambda a, b: a or b,
                T_IN_ENUM_VAL: eval_different_in,
            }

            if op not in supported_types and (type(left), type(right), op) not in supported_types:
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
        same_type = (int, float, bool)
        dispatcher = eval_different_bin_op
        if type_left is type_right or (type_left in same_type and type_right in same_type):
            dispatcher = type_dispatch[type_left]
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
            if type(operand) in (int, float):
                return -operand
            raise EvaluatorError(
                self.file,
                f"unary negation not supported on type {type(operand)}",
                root.meta_data.line,
                root.meta_data.column_start,
                root.meta_data.column_end,
            )

        def eval_uplus(operand):
            if type(operand) in (int, float):
                return +operand
            raise EvaluatorError(
                self.file,
                f"unary plus not supported on type {type(operand)}",
                root.meta_data.line,
                root.meta_data.column_start,
                root.meta_data.column_end,
            )

        operator_dispatch = {
            T_NEGATE_ENUM_VAL: eval_negate,
            T_UMINUS_ENUM_VAL: eval_uminus,
            T_UPLUS_ENUM_VAL: eval_uplus,
        }
        op_id = root.op
        operand = self.eval_expression(root.operand)

        return operator_dispatch[op_id](operand)

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
