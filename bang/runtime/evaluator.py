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
from math import isfinite

from bang.calling import bind_arguments
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
    INTERPOLATED_STRING_NODE_CLASS,
    NONE_LITERAL_NODE_CLASS,
    RETURN_NODE_CLASS,
    SLICE_NODE_CLASS,
    STRING_LITERAL_NODE_CLASS,
    UNARY_OP_NODE_CLASS,
    WHILE_NODE_CLASS,
)
from bang.runtime.evaluator_nodes import (
    RUN_TIME_BUILTIN,
    RUN_TIME_DATACLASS,
    RUN_TIME_FUNCTION,
    RUN_TIME_INSTANCE,
    format_value,
)


_MISSING = object()


class EvaluatorError(Exception):
    def __init__(self, text, msg, row, start, end):
        self.text = text
        self.msg = msg
        self.row = row
        self.start = start
        self.end = end

        super().__init__(self._format())

    def _get_real_error_line(self):
        lines = self.text.rstrip("\0").splitlines()
        # Row is 1-based in tokens, so -1 for index
        if 0 <= self.row - 1 < len(lines):
            return lines[self.row - 1]
        return ""

    def _format(self):
        error_line = self._get_real_error_line()
        crt_length = self.end - self.start if self.end - self.start != 0 else 1
        pointers = " " * (self.start - 1) + "^" * crt_length
        return (
            f"[EvaluatorError] Line {self.row}, Column {self.start}-{self.end}:\n"
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
    MAX_CALL_DEPTH = 64

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
    INTERPOLATED_STRING_NODE_CLASS = INTERPOLATED_STRING_NODE_CLASS
    SLICE_NODE_CLASS = SLICE_NODE_CLASS
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
            print(*(format_value(value) for value in args))
            return 0

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

            if all(isinstance(value, (int, float)) for value in args):
                return sum(args)
            expected_type = type(args[0])
            factories = {str: str, list: list, set: set, dict: dict}
            if expected_type not in factories:
                raise EvaluatorError(
                    self.file,
                    "sum expects numbers, strings, arrays, sets, or dictionaries",
                    meta_data.line,
                    meta_data.column_start,
                    meta_data.column_end,
                )
            base = factories[expected_type]()
            for value in args:
                if type(value) is not expected_type:
                    raise EvaluatorError(
                        self.file,
                        "sum expects homogeneous values or numeric values",
                        meta_data.line,
                        meta_data.column_start,
                        meta_data.column_end,
                    )
                base = base | value if expected_type in (set, dict) else base + value
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
            for i in args[1:]:
                if type(i) is not expected_type and not (
                    isinstance(base, (int, float)) and isinstance(i, (int, float))
                ):
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
            for i in args[1:]:
                if type(i) is not expected_type and not (
                    isinstance(base, (int, float)) and isinstance(i, (int, float))
                ):
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
            if not args:
                raise EvaluatorError(
                    self.file,
                    "sort function expects atleast one arg",
                    meta_data.line,
                    meta_data.column_start,
                    meta_data.column_end,
                )
            if len(args) == 1:
                if type(args[0]) is list:
                    args = args[0]
                elif type(args[0]) is set:
                    args = list(args[0])
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
        self.built_in_functions = {
            name: RUN_TIME_BUILTIN(name, implementation)
            for name, implementation in self.built_in_functions.items()
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
            try:
                self.eval_construct(construct)
            except RecursionError as error:
                metadata = getattr(construct, "meta_data", None)
                raise EvaluatorError(
                    self.file,
                    "maximum evaluation nesting exceeded",
                    metadata.line if metadata else 1,
                    metadata.column_start if metadata else 1,
                    metadata.column_end if metadata else 2,
                ) from error

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
        declaration = self.RUN_TIME_DATACLASS(fields=tuple(dataclass_fields), name=dataclass_name)
        self.initalize_var(dataclass_name, declaration)

    def eval_function(self, root):
        self.initalize_var(root.name, self._make_function(root))

    def _make_function(self, root, *, binding_name=None):
        # with this, were limiting the number of frames on the scope stack at function creation
        # but were not limiting the contents of those frames.
        # so, we're saying, if this function was declared on the
        # 7th scope, this function can only see the seven scopes
        # (no new scopes the function can see)
        # but we can add infinitely many new variables to those frozen
        # scopes (because we want the function to be able to, say, call itself)
        closure = self.scope_stack[:]

        return self.RUN_TIME_FUNCTION(
            body=root.body,
            params_name=root.arg_list_name,
            closure=closure,
            parameters=root.parameters,
            name=root.name or binding_name,
            line=root.meta_data.line,
        )

    def eval_block(self, root):
        # A block just evals its children in the current scope

        for construct in root.block:
            self.eval_construct(construct)

    def _eval_scoped_block(self, block):
        self.scope_stack.append({})
        try:
            self.eval_block(block)
        finally:
            self.scope_stack.pop()

    def eval_if(self, root):
        if self.eval_expression(root.condition.root_expr):
            self._eval_scoped_block(root.body)
            return
        for branch in root.elif_branch.block:
            if self.eval_expression(branch.condition.root_expr):
                self._eval_scoped_block(branch.body)
                return
        for branch in root.else_branch.block:
            self._eval_scoped_block(branch.body)
            return

    def eval_for(self, root):
        bound = self.eval_expression(root.bound.root_expr)
        if isinstance(bound, int):
            iterator = iter(range(0, bound, -1 if bound < 0 else 1))
        else:
            try:
                iterator = iter(bound)
            except TypeError:
                raise EvaluatorError(
                    self.file,
                    "bound not iterable",
                    root.meta_data.line,
                    root.meta_data.column_start,
                    root.meta_data.column_end,
                ) from None

        self.loop_depth += 1
        self.scope_stack.append({})
        try:
            while True:
                try:
                    value = next(iterator)
                except StopIteration:
                    break
                except RuntimeError as error:
                    raise EvaluatorError(
                        self.file,
                        "collection changed during iteration",
                        root.meta_data.line,
                        root.meta_data.column_start,
                        root.meta_data.column_end,
                    ) from error
                if type(root.variable) is self.IDENTIFIER_NODE_CLASS:
                    self.initalize_var(root.variable.value, value)
                else:
                    self._eval_assignment(
                        root.variable, self.T_ASSIGN_ENUM_VAL, root, lambda value=value: value
                    )
                try:
                    self.eval_block(root.body)
                except _ContinueSignal:
                    continue
                except _BreakSignal:
                    break
        finally:
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
                if scope[name] is _MISSING:
                    raise EvaluatorError(
                        self.file,
                        f"parameter '{name}' read before binding",
                        potential_error.line,
                        potential_error.column_start,
                        potential_error.column_end,
                    )
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
        def evaluate_rhs():
            expression = root.right_hand.root_expr
            if (
                root.op == self.T_ASSIGN_ENUM_VAL
                and type(root.left_hand) is self.IDENTIFIER_NODE_CLASS
                and type(expression) is self.FUNCTION_NODE_CLASS
            ):
                return self._make_function(expression, binding_name=root.left_hand.value)
            return self.eval_expression(expression)

        self._eval_assignment(
            root.left_hand,
            root.op,
            root,
            evaluate_rhs,
        )

    def _read_index(self, base, key, metadata):
        if isinstance(key, slice) and type(base) not in (list, str):
            raise EvaluatorError(
                self.file,
                "slicing requires an array or string",
                metadata.line,
                metadata.column_start,
                metadata.column_end,
            )
        try:
            return base[key]
        except (IndexError, KeyError, TypeError, ValueError) as error:
            raise EvaluatorError(
                self.file,
                "invalid index or index out of bounds",
                metadata.line,
                metadata.column_start,
                metadata.column_end,
            ) from error

    def _eval_assignment(self, left_hand, op, location, evaluate_rhs):
        """Share assignment binding with loops while preserving RHS evaluation order."""
        compound = op != self.T_ASSIGN_ENUM_VAL

        def fail(message):
            raise EvaluatorError(
                self.file,
                message,
                location.meta_data.line,
                location.meta_data.column_start,
                location.meta_data.column_end,
            )

        def resolve_target(left_hand, *, create=False):
            """Resolve a writable container/key pair, evaluating its parts once."""
            if type(left_hand) is self.IDENTIFIER_NODE_CLASS:
                name = left_hand.value
                for scope in reversed(self.scope_stack):
                    if name in scope:
                        return scope, name
                if create:
                    return self.scope_stack[-1], name
                fail(f"Variable {name} not found in current scope")

            if type(left_hand) is self.INDEX_NODE_CLASS:
                target = self.eval_expression(left_hand.base)
                try:
                    for index in left_hand.index[:-1]:
                        target = self._read_index(
                            target, self.eval_expression(index.root_expr), left_hand.meta_data
                        )
                    return target, self.eval_expression(left_hand.index[-1].root_expr)
                except (IndexError, TypeError, KeyError):
                    fail("Index out of bounds")

            if type(left_hand) is self.FIELD_ACCESS_NODE_CLASS:
                target = self.eval_expression(left_hand.base)
                for index, name in enumerate(left_hand.field):
                    if type(target) is not self.RUN_TIME_INSTANCE:
                        fail("field access is only performable on instances of classes")
                    if name not in target.fields:
                        fail("field name was not included in the dataclass definition")
                    if index == len(left_hand.field) - 1:
                        return target.fields, name
                    target = target.fields[name]
            fail("invalid assignment target")

        def read_target(target, key):
            if isinstance(key, slice) and type(target) not in (list, str):
                fail("slicing requires an array or string")
            try:
                return target[key]
            except (IndexError, TypeError, KeyError, ValueError):
                fail("Index out of bounds")

        def write_target(target, key, value):
            if isinstance(key, slice):
                if type(target) is not list or type(value) is not list:
                    fail("slice assignment requires an array target and array value")
            try:
                target[key] = value
            except ValueError:
                fail("extended slice assignment length mismatch")
            except (IndexError, TypeError, KeyError):
                fail("invalid assignment target or index")

        def combine(current, value):
            operation = self.BIN_OP_NODE_CLASS(
                left=None,
                op=self.ASSIGNMENT_TO_NORMAL_OPS[op],
                right=None,
                meta_data=location.meta_data,
            )
            return self._eval_binary_values(operation, current, value)

        def assign(left_hand, value):
            if type(left_hand) is self.ARRAY_LITERAL_NODE_CLASS:
                if type(value) is not list:
                    fail("multi-variable assignment right hand must be type list")
                if len(left_hand.elements) > len(value):
                    fail("not enough values to unpack")
                for element, item in zip(left_hand.elements, value, strict=False):
                    assign(element.root_expr, item)
                return

            target, key = resolve_target(left_hand, create=not compound)
            if compound:
                value = combine(read_target(target, key), value)
            write_target(target, key, value)

        if compound and type(left_hand) is not self.ARRAY_LITERAL_NODE_CLASS:
            target, key = resolve_target(left_hand)
            current = read_target(target, key)
            value = evaluate_rhs()
            write_target(target, key, combine(current, value))
        else:
            assign(left_hand, evaluate_rhs())

    # this function handles all expression level contructs such as literals, binary ops,
    # unary ops, and function calls
    def eval_expression(self, root):
        """Evaluate an expression with an explicit stack and left-to-right effects."""
        tasks = [("eval", root)]
        values = []
        raw_types = (
            int,
            bool,
            str,
            float,
            list,
            set,
            dict,
            self.RUN_TIME_FUNCTION,
            self.RUN_TIME_DATACLASS,
            self.RUN_TIME_INSTANCE,
            RUN_TIME_BUILTIN,
        )
        while tasks:
            task = tasks.pop()
            tag, node = task[:2]
            if tag == "eval":
                typ = type(node)
                if typ in raw_types:
                    values.append(node)
                elif node is None:
                    values.append(0)
                elif typ is self.EXPRESSION_NODE_CLASS:
                    tasks.append(("eval", node.root_expr))
                elif typ in self.LITERALS:
                    values.append(self.LITERALS[typ](node.value))
                elif typ is self.IDENTIFIER_NODE_CLASS:
                    frame = self.scope_stack[self.search_for_var(node.value, node.meta_data)]
                    values.append(frame[node.value])
                elif typ is self.FUNCTION_NODE_CLASS:
                    values.append(self._make_function(node))
                elif typ is self.SLICE_NODE_CLASS:
                    parts = (node.start, node.stop, node.step)
                    tasks.append(("slice", node, sum(part is not None for part in parts)))
                    tasks.extend(
                        ("eval", part.root_expr) for part in reversed(parts) if part is not None
                    )
                elif typ is self.INTERPOLATED_STRING_NODE_CLASS:
                    tasks.append(("interpolation", node, 0, []))
                elif typ is self.BIN_OP_NODE_CLASS:
                    tasks.extend((("binary_left", node), ("eval", node.left)))
                elif typ is self.UNARY_OP_NODE_CLASS:
                    tasks.extend((("unary", node), ("eval", node.operand)))
                elif typ is self.ARRAY_LITERAL_NODE_CLASS:
                    tasks.append(("array", node, len(node.elements)))
                    tasks.extend(("eval", item.root_expr) for item in reversed(node.elements))
                elif typ is self.INDEX_NODE_CLASS:
                    tasks.extend((("index", node, 0), ("eval", node.base)))
                elif typ is self.FIELD_ACCESS_NODE_CLASS:
                    tasks.extend((("field", node), ("eval", node.base)))
                elif typ is self.CALL_NODE_CLASS:
                    tasks.extend((("callee", node), ("eval", node.name)))
                else:
                    raise EvaluatorError(self.file, "invalid expression node", 1, 1, 2)
            elif tag == "binary_left":
                left = values.pop()
                if (
                    node.op == self.T_AND_ENUM_VAL
                    and not left
                    or node.op == self.T_OR_ENUM_VAL
                    and left
                ):
                    values.append(left)
                elif node.op in (self.T_AND_ENUM_VAL, self.T_OR_ENUM_VAL):
                    tasks.append(("eval", node.right))
                else:
                    tasks.extend((("binary_right", node, left), ("eval", node.right)))
            elif tag == "binary_right":
                values.append(self._eval_binary_values(node, task[2], values.pop()))
            elif tag == "unary":
                values.append(self._eval_unary_values(node, values.pop()))
            elif tag == "array":
                count = task[2]
                result = values[-count:] if count else []
                if count:
                    del values[-count:]
                values.append(result)
            elif tag == "index":
                base, position = values.pop(), task[2]
                if position == len(node.index):
                    values.append(base)
                else:
                    tasks.extend(
                        (
                            ("indexed", node, position, base),
                            ("eval", node.index[position].root_expr),
                        )
                    )
            elif tag == "indexed":
                value = self._read_index(task[3], values.pop(), node.meta_data)
                values.append(value)
                tasks.append(("index", node, task[2] + 1))
            elif tag == "slice":
                count = task[2]
                supplied = values[-count:] if count else []
                if count:
                    del values[-count:]
                iterator = iter(supplied)
                parts = [
                    next(iterator) if part is not None else None
                    for part in (node.start, node.stop, node.step)
                ]
                if any(value is not None and not isinstance(value, int) for value in parts):
                    raise EvaluatorError(
                        self.file,
                        "slice bounds and step must be integers",
                        node.meta_data.line,
                        node.meta_data.column_start,
                        node.meta_data.column_end,
                    )
                if parts[2] == 0:
                    raise EvaluatorError(
                        self.file,
                        "slice step cannot be zero",
                        node.meta_data.line,
                        node.meta_data.column_start,
                        node.meta_data.column_end,
                    )
                values.append(slice(*parts))
            elif tag == "interpolation":
                position, output = task[2:]
                if position == len(node.parts):
                    values.append("".join(output))
                else:
                    part = node.parts[position]
                    if isinstance(part, str):
                        output.append(part)
                        tasks.append(("interpolation", node, position + 1, output))
                    else:
                        tasks.extend(
                            (("interpolated", node, position, output), ("eval", part.root_expr))
                        )
            elif tag == "interpolated":
                position, output = task[2:]
                try:
                    output.append(format_value(values.pop()))
                except (ValueError, OverflowError, RecursionError) as error:
                    metadata = node.parts[position].root_expr.meta_data
                    raise EvaluatorError(
                        self.file,
                        "value cannot be formatted as a string",
                        metadata.line,
                        metadata.column_start,
                        metadata.column_end,
                    ) from error
                tasks.append(("interpolation", node, position + 1, output))
            elif tag == "field":
                value = values.pop()
                for name in node.field:
                    if type(value) is not self.RUN_TIME_INSTANCE or name not in value.fields:
                        raise EvaluatorError(
                            self.file,
                            "field is not defined on this instance",
                            node.meta_data.line,
                            node.meta_data.column_start,
                            node.meta_data.column_end,
                        )
                    value = value.fields[name]
                values.append(value)
            elif tag == "callee":
                callee = values.pop()
                tasks.append(("call", node, callee, len(node.args)))
                tasks.extend(("eval", item.root_expr) for item in reversed(node.args))
            elif tag == "call":
                count = task[3]
                args = values[-count:] if count else []
                if count:
                    del values[-count:]
                values.append(
                    self._invoke_callable(task[2], args, node.meta_data, node.keyword_names)
                )
        return values.pop()

    def _invoke_callable(self, callee, args, metadata, keyword_names=()):
        if type(callee) is self.RUN_TIME_FUNCTION:
            return self.eval_call(callee, args, metadata, keyword_names)
        if keyword_names:
            raise EvaluatorError(
                self.file,
                "named arguments require a function with declared parameters",
                metadata.line,
                metadata.column_start,
                metadata.column_end,
            )
        if type(callee) is self.RUN_TIME_DATACLASS:
            if len(args) > len(callee.fields):
                raise EvaluatorError(
                    self.file,
                    f"{callee.name} received too many constructor arguments",
                    metadata.line,
                    metadata.column_start,
                    metadata.column_end,
                )
            fields = {
                name: args[index] if index < len(args) else 0
                for index, name in enumerate(callee.fields)
            }
            return self.RUN_TIME_INSTANCE(of=callee, fields=fields)
        if callable(callee) and callee in self.built_in_function_objects:
            try:
                result = self._checked_real_result(callee(args, metadata))
            except (TypeError, ValueError, ArithmeticError, RecursionError) as error:
                raise EvaluatorError(
                    self.file,
                    f"invalid builtin operation: {error}",
                    metadata.line,
                    metadata.column_start,
                    metadata.column_end,
                ) from error
            return 0 if result is None else result
        raise EvaluatorError(
            self.file,
            "attempt to call a non-function",
            metadata.line,
            metadata.column_start,
            metadata.column_end,
        )

    # -------------------------------------------
    # BINARY OPERATIONS START
    # -------------------------------------------

    def eval_bin_ops(self, root):
        left = self.eval_expression(root.left)
        if root.op == self.T_AND_ENUM_VAL:
            return self.eval_expression(root.right) if left else left
        if root.op == self.T_OR_ENUM_VAL:
            return left if left else self.eval_expression(root.right)
        right = self.eval_expression(root.right)
        return self._eval_binary_values(root, left, right)

    @staticmethod
    def _checked_real_result(result):
        if isinstance(result, complex) or (isinstance(result, float) and not isfinite(result)):
            raise ValueError("numeric result is outside the supported real-number range")
        return result

    def _eval_binary_values(self, root, left, right):
        try:
            return self._checked_real_result(self._apply_binary_values(root, left, right))
        except (TypeError, ValueError, ArithmeticError, RecursionError) as error:
            raise EvaluatorError(
                self.file,
                f"invalid operator operands or numeric result: {error}",
                root.meta_data.line,
                root.meta_data.column_start,
                root.meta_data.column_end,
            ) from error

    def _apply_binary_values(self, root, left, right):
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
        if op in (T_EQ_ENUM_VAL, T_NEQ_ENUM_VAL):
            return left == right if op == T_EQ_ENUM_VAL else left != right
        # Booleans participate in all numeric overloads like 0 and 1.
        if type(left) is bool:
            left = int(left)
        if type(right) is bool:
            right = int(right)
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
                return self._checked_real_result(a / b if div_type == "true" else a // b)

            def list_sub(a, b):
                try:
                    to_remove = set(b)
                    return [x for x in a if x not in to_remove]
                except TypeError:
                    return [x for x in a if x not in b]

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
                        return [self._checked_real_result(x * multiplier) for x in base]
                    else:
                        return [
                            self._checked_real_result(i * j) for i, j in zip(a, b, strict=False)
                        ]
                else:
                    # this will be where operations such as [1] * 3
                    # go which we will need to change semantic pass to allow
                    pass

            def list_divide(a, b, kind):
                if len(a) == len(b):
                    return [list_div_helper(x, y, kind) for x, y in zip(a, b, strict=False)]
                if len(a) == 1:
                    return [list_div_helper(a[0], y, kind) for y in b]
                if len(b) == 1:
                    return [list_div_helper(x, b[0], kind) for x in a]
                raise EvaluatorError(
                    self.file,
                    "list division requires equal lengths or a singleton operand",
                    root.meta_data.line,
                    root.meta_data.column_start,
                    root.meta_data.column_end,
                )

            def list_div(a, b):
                return list_divide(a, b, "true")

            def list_floor_div(a, b):
                return list_divide(a, b, "floor")

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
            dispatcher = type_dispatch.get(type_left, eval_different_bin_op)
        return dispatcher(left, op, right)

    # -------------------------------------------
    # BINARY OPERATIONS END
    # -------------------------------------------

    # -------------------------------------------
    # UNARY OPERATIONS START
    # -------------------------------------------

    def eval_unary_ops(self, root):
        return self._eval_unary_values(root, self.eval_expression(root.operand))

    def _eval_unary_values(self, root, operand):
        # since each unary operation is pretty clear on what it does
        # we will dispatch based on unary operator not type

        def eval_negate(operand):
            return not operand

        def eval_uminus(operand):
            if isinstance(operand, (int, float)):
                return -operand
            raise EvaluatorError(
                self.file,
                f"unary negation not supported on type {type(operand)}",
                root.meta_data.line,
                root.meta_data.column_start,
                root.meta_data.column_end,
            )

        def eval_uplus(operand):
            if isinstance(operand, (int, float)):
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
        return operator_dispatch[op_id](operand)

    # -------------------------------------------
    # UNARY OPERATIONS END
    # -------------------------------------------

    def eval_call(self, callee, args, meta_data, keyword_names=()):
        if self.func_depth >= self.MAX_CALL_DEPTH:
            raise EvaluatorError(
                self.file,
                f"function call depth exceeds the limit of {self.MAX_CALL_DEPTH}",
                meta_data.line,
                meta_data.column_start,
                meta_data.column_end,
            )
        parameters = callee.parameters
        if parameters is None:
            if keyword_names:
                raise EvaluatorError(
                    self.file,
                    "variadic functions accept positional arguments only",
                    meta_data.line,
                    meta_data.column_start,
                    meta_data.column_end,
                )
            frame = {callee.params_name: args}
        else:
            signature = tuple((p.name, p.default is not None) for p in parameters)
            try:
                supplied = bind_arguments(
                    signature, args, keyword_names, variadic_name=callee.params_name
                )
            except ValueError as error:
                raise EvaluatorError(
                    self.file,
                    str(error),
                    meta_data.line,
                    meta_data.column_start,
                    meta_data.column_end,
                ) from error
            frame = {p.name: _MISSING for p in parameters}
            if callee.params_name is not None:
                frame[callee.params_name] = supplied[callee.params_name]
        saved_stack = self.scope_stack
        saved_loop_depth = self.loop_depth
        self.scope_stack = list(callee.closure) + [frame]
        self.loop_depth = 0
        self.func_depth += 1
        try:
            if parameters is not None:
                for parameter in parameters:
                    frame[parameter.name] = (
                        supplied[parameter.name]
                        if parameter.name in supplied
                        else self.eval_expression(parameter.default.root_expr)
                    )
            try:
                self.eval_block(callee.body)
            except _ReturnSignal as sig:
                return sig.value
        finally:
            self.scope_stack = saved_stack
            self.loop_depth = saved_loop_depth
            self.func_depth -= 1
        return 0
