# Best-effort checks for bindings, known types, and control-flow placement.
# Dynamic values and facts that differ across paths are checked at runtime.

from copy import deepcopy

from bang.builtin_specs import SPECS
from bang.calling import bind_arguments
from bang.diagnostics import (
    expression_location,
    field_error_message,
    field_location,
    index_error_message,
    index_location,
    nonindexable_message,
    operator_message,
    render_error,
    type_name,
)
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
    INTERPOLATED_STRING_NODE_CLASS,
    NONE_LITERAL_NODE_CLASS,
    RETURN_NODE_CLASS,
    SLICE_NODE_CLASS,
    STRING_LITERAL_NODE_CLASS,
    UNARY_OP_NODE_CLASS,
    WHILE_NODE_CLASS,
)
from bang.semantic.builtin_analysis import infer_builtin
from bang.semantic.semantic_nodes import (
    ARRAY_TYPE_CLASS,
    BOOL_TYPE_CLASS,
    DATA_CLASS_TYPE_CLASS,
    DICT_TYPE_CLASS,
    DYNAMIC_TYPE_CLASS,
    FUNCTION_TYPE_CLASS,
    FROZEN_SET_TYPE_CLASS,
    INSTANCE_TYPE_CLASS,
    NONE_TYPE_CLASS,
    NUMBER_TYPE_CLASS,
    SET_TYPE_CLASS,
    SLICE_TYPE_CLASS,
    STRING_TYPE_CLASS,
    BuiltinType,
)


class SemanticError(Exception):
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
        return render_error(
            "SemanticError", self.text, self.msg, self.row, self.start, self.end
        )

    def __str__(self) -> str:
        return self._format()

    __repr__ = __str__


class SemanticAnalysis:
    # SEMANTIC TYPES

    ARRAY_TYPE_CLASS = ARRAY_TYPE_CLASS
    BOOL_TYPE_CLASS = BOOL_TYPE_CLASS
    DATA_CLASS_TYPE_CLASS = DATA_CLASS_TYPE_CLASS
    DICT_TYPE_CLASS = DICT_TYPE_CLASS
    DYNAMIC_TYPE_CLASS = DYNAMIC_TYPE_CLASS
    FUNCTION_TYPE_CLASS = FUNCTION_TYPE_CLASS
    INSTANCE_TYPE_CLASS = INSTANCE_TYPE_CLASS
    NONE_TYPE_CLASS = NONE_TYPE_CLASS
    NUMBER_TYPE_CLASS = NUMBER_TYPE_CLASS
    SET_TYPE_CLASS = SET_TYPE_CLASS
    FROZEN_SET_TYPE_CLASS = FROZEN_SET_TYPE_CLASS
    SLICE_TYPE_CLASS = SLICE_TYPE_CLASS
    STRING_TYPE_CLASS = STRING_TYPE_CLASS

    # PARSER NODES

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
    INTERPOLATED_STRING_NODE_CLASS = INTERPOLATED_STRING_NODE_CLASS
    SLICE_NODE_CLASS = SLICE_NODE_CLASS
    STRING_LITERAL_NODE_CLASS = STRING_LITERAL_NODE_CLASS
    UNARY_OP_NODE_CLASS = UNARY_OP_NODE_CLASS
    WHILE_NODE_CLASS = WHILE_NODE_CLASS
    BLOCK_NODE_CLASS = BLOCK_NODE_CLASS

    # LEXER_ENUMS

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

    BUILT_IN_FUNCTIONS = {name: FUNCTION_TYPE_CLASS for name in SPECS}

    LITERALS = {
        INTEGER_LITERAL_NODE_CLASS: NUMBER_TYPE_CLASS,
        FLOAT_LITERAL_NODE_CLASS: NUMBER_TYPE_CLASS,
        STRING_LITERAL_NODE_CLASS: STRING_TYPE_CLASS,
        BOOLEAN_LITERAL_NODE_CLASS: BOOL_TYPE_CLASS,
        NONE_LITERAL_NODE_CLASS: NONE_TYPE_CLASS,
    }

    ARITH_OPS = {
        T_PLUS_ENUM_VAL,
        T_MINUS_ENUM_VAL,
        T_ASTERISK_ENUM_VAL,
        T_SLASH_ENUM_VAL,
        T_DSLASH_ENUM_VAL,
        T_EXPO_ENUM_VAL,
    }

    ASSIGNMENT_TO_NORMAL = {
        T_PLUS_ASSIGN_ENUM_VAL: T_PLUS_ENUM_VAL,
        T_MINUS_ASSIGN_ENUM_VAL: T_MINUS_ENUM_VAL,
        T_ASTERISK_ASSIGN_ENUM_VAL: T_ASTERISK_ENUM_VAL,
        T_SLASH_ASSIGN_ENUM_VAL: T_SLASH_ENUM_VAL,
    }

    ARITH_ASSIGNMENTS = {
        T_PLUS_ASSIGN_ENUM_VAL,
        T_MINUS_ASSIGN_ENUM_VAL,
        T_SLASH_ASSIGN_ENUM_VAL,
        T_ASTERISK_ASSIGN_ENUM_VAL,
    }

    ALLOWED_UNARY_OPS = {
        NUMBER_TYPE_CLASS,
    }

    UNHASHABLE_TYPES = {
        ARRAY_TYPE_CLASS,
        DICT_TYPE_CLASS,
        SET_TYPE_CLASS,
    }

    BIN_OP_DIFFERENT_RULES = {
        # I honestly should just merge number type and booltype
        # but thatll be for another day
        (STRING_TYPE_CLASS, NUMBER_TYPE_CLASS, T_ASTERISK_ENUM_VAL): STRING_TYPE_CLASS,
        (NUMBER_TYPE_CLASS, STRING_TYPE_CLASS, T_ASTERISK_ENUM_VAL): STRING_TYPE_CLASS,
        (STRING_TYPE_CLASS, BOOL_TYPE_CLASS, T_ASTERISK_ENUM_VAL): STRING_TYPE_CLASS,
        (BOOL_TYPE_CLASS, STRING_TYPE_CLASS, T_ASTERISK_ENUM_VAL): STRING_TYPE_CLASS,
        (ARRAY_TYPE_CLASS, NUMBER_TYPE_CLASS, T_ASTERISK_ENUM_VAL): ARRAY_TYPE_CLASS,
        (NUMBER_TYPE_CLASS, ARRAY_TYPE_CLASS, T_ASTERISK_ENUM_VAL): ARRAY_TYPE_CLASS,
        (ARRAY_TYPE_CLASS, BOOL_TYPE_CLASS, T_ASTERISK_ENUM_VAL): ARRAY_TYPE_CLASS,
        (BOOL_TYPE_CLASS, ARRAY_TYPE_CLASS, T_ASTERISK_ENUM_VAL): ARRAY_TYPE_CLASS,
    }

    def __init__(self, file, roots):
        self.file = file
        self.roots = roots
        # the scope stack is the only semi confusing
        # thing about semantic analysis really, everything else
        # is just psuedo-intepreting to type check.
        # but really all were doing is saying, if we
        # enter a new scope, push
        # a new scope level to our stack, if we exit a
        # scope, pop a scope off our stack.
        # if we see an assignment, record the assignment
        # in our current scope level.

        self.scope_stack = [{}]

        self.scope_stack[0].update({name: BuiltinType(name) for name in self.BUILT_IN_FUNCTIONS})

        self.CONSTRUCTS_TO_WALK = {
            self.ASSIGNMENT_NODE_CLASS: self.walk_assignments,
            self.IF_NODE_CLASS: self.walk_if,
            self.ELIF_NODE_CLASS: self.walk_elif,
            self.ELSE_NODE_CLASS: self.walk_else,
            self.FOR_NODE_CLASS: self.walk_for,
            self.WHILE_NODE_CLASS: self.walk_while,
            self.BLOCK_NODE_CLASS: self.walk_block,
            self.BREAK_NODE_CLASS: self.walk_break,
            self.CONTINUE_NODE_CLASS: self.walk_continue,
            self.RETURN_NODE_CLASS: self.walk_return,
            self.EXPRESSION_NODE_CLASS: self.walk_expression,
            self.FUNCTION_NODE_CLASS: self.walk_function,
            self.CALL_NODE_CLASS: self.walk_expression,
            self.DATA_CLASS_NODE_CLASS: self.walk_dataclass,
        }

        # we need to know the loop depth for the break/continue etc constructs
        # because if we see a break outside of a loop for example we can throw an error
        self.loop_depth = 0
        self.func_depth = 0

    def walk_program(self):
        for construct in self.roots:
            try:
                self.walk_construct(construct)
            except RecursionError as error:
                metadata = getattr(construct, "meta_data", None)
                raise SemanticError(
                    self.file,
                    "maximum analysis nesting exceeded",
                    metadata.line if metadata else 1,
                    metadata.column_start if metadata else 1,
                    metadata.column_end if metadata else 2,
                ) from error

    # could probably use this walk_construct more
    # typically but its clearer to just call the specific expression
    # in some cases although this could change
    def walk_construct(self, root):
        handler = self.CONSTRUCTS_TO_WALK[type(root)]
        return handler(root)

    def walk_function(self, root):
        self._function_type(root, binding_name=root.name)

    def _function_type(self, root, *, binding_name=None):
        parameters = root.parameters
        signature = (
            None
            if parameters is None
            else tuple((p.name, p.default is not None) for p in parameters)
        )
        function_type = self.FUNCTION_TYPE_CLASS(
            parameters=signature, variadic_name=root.arg_list_name
        )
        if binding_name is not None:
            self.initalize_var(binding_name, function_type)
        saved_scopes = self.scope_stack
        saved_loop_depth = self.loop_depth
        parameter_names = set() if parameters is None else {p.name for p in parameters}
        if root.arg_list_name is not None:
            parameter_names.add(root.arg_list_name)
        self.scope_stack = [
            {name: self.DYNAMIC_TYPE_CLASS() for name in scope if name not in parameter_names}
            for scope in saved_scopes
        ] + [{}]
        self.loop_depth = 0
        self.func_depth += 1
        try:
            if root.arg_list_name is not None:
                self.scope_stack[-1][root.arg_list_name] = self.DYNAMIC_TYPE_CLASS()
            if parameters is not None:
                for parameter in parameters:
                    if parameter.default is not None:
                        self.walk_expression(parameter.default.root_expr)
                    self.scope_stack[-1][parameter.name] = self.DYNAMIC_TYPE_CLASS()
            self.walk_block(root.body)
        finally:
            self.scope_stack = saved_scopes
            self.loop_depth = saved_loop_depth
            self.func_depth -= 1
        return function_type

    def walk_dataclass(self, root):
        dataclass_name = root.name
        # removing duplicate names
        seen = set()
        dataclass_fields = [f for f in root.fields if not (f in seen or seen.add(f))]
        declaration = self.DATA_CLASS_TYPE_CLASS(fields=tuple(dataclass_fields))
        self.initalize_var(dataclass_name, declaration)

    def walk_block(self, root):
        # A block just walks its children in the current scope

        for construct in root.block:
            self.walk_construct(construct)

    def _widen_loop_bindings(self, root):
        """Assignments may have run on a previous iteration of this loop."""
        written = set()

        def target_names(target):
            typ = type(target)
            if typ is self.IDENTIFIER_NODE_CLASS:
                written.add(target.value)
            elif typ is self.ARRAY_LITERAL_NODE_CLASS:
                for element in target.elements:
                    target_names(element.root_expr)
            elif typ in (self.INDEX_NODE_CLASS, self.FIELD_ACCESS_NODE_CLASS):
                target_names(target.base)

        def visit(node):
            typ = type(node)
            if typ is self.ASSIGNMENT_NODE_CLASS:
                target_names(node.left_hand)
                return
            if typ in (self.FUNCTION_NODE_CLASS, self.DATA_CLASS_NODE_CLASS):
                written.add(node.name)
                return
            if typ is self.FOR_NODE_CLASS:
                target_names(node.variable)
            for name in ("body", "elif_branch", "else_branch"):
                block = getattr(node, name, None)
                if block is not None:
                    for child in block.block:
                        visit(child)

        visit(root)
        for name in written:
            for scope in reversed(self.scope_stack):
                if name in scope:
                    self._invalidate_mutable_facts([scope[name]])
                    scope[name] = self.DYNAMIC_TYPE_CLASS()
                    break

    def _walk_scoped_path(self, root, *, loop_target=None, check_condition=True):
        """Check one possible path without changing another path's input."""
        saved_scopes = self.scope_stack
        self.scope_stack = deepcopy(saved_scopes)
        try:
            if type(root) in (self.FOR_NODE_CLASS, self.WHILE_NODE_CLASS):
                self._widen_loop_bindings(root)
            if check_condition and hasattr(root, "condition"):
                self.walk_expression(root.condition.root_expr)
            self.scope_stack.append({})
            if loop_target is not None:
                if type(loop_target) is self.IDENTIFIER_NODE_CLASS:
                    self.initalize_var(loop_target.value, self.DYNAMIC_TYPE_CLASS())
                else:
                    self._walk_assignment(
                        loop_target, self.T_ASSIGN_ENUM_VAL, root, self.DYNAMIC_TYPE_CLASS
                    )
            self.walk_block(root.body)
            self.scope_stack.pop()
            return self.scope_stack
        finally:
            self.scope_stack = saved_scopes

    def _merge_control_paths(self, paths):
        """Preserve only facts common to the incoming state and every path."""
        scalar_types = (
            self.NUMBER_TYPE_CLASS,
            self.BOOL_TYPE_CLASS,
            self.STRING_TYPE_CLASS,
            self.NONE_TYPE_CLASS,
            self.ARRAY_TYPE_CLASS,
            self.SET_TYPE_CLASS,
            self.FROZEN_SET_TYPE_CLASS,
            self.DICT_TYPE_CLASS,
        )
        bindings = []
        owners = {}
        ambiguous = set()
        for depth, scope in enumerate(self.scope_stack):
            for name, before in scope.items():
                options = [before] + [path[depth][name] for path in paths]
                signature = None
                if type(before) is self.INSTANCE_TYPE_CLASS and all(
                    type(value) is self.INSTANCE_TYPE_CLASS and value.of is before.of
                    for value in options
                ):
                    signature = tuple(id(value) for value in options)
                    for position, value in enumerate(options):
                        previous = owners.setdefault((position, id(value)), signature)
                        if previous != signature:
                            ambiguous.update((previous, signature))
                bindings.append((scope, name, before, options, signature))

        records = {}
        for scope, name, before, options, signature in bindings:
            typ = type(before)
            if typ in scalar_types and all(type(value) is typ for value in options):
                scope[name] = typ(None)
            elif typ in (
                BuiltinType,
                self.FUNCTION_TYPE_CLASS,
                self.DATA_CLASS_TYPE_CLASS,
            ) and all(value is before for value in options):
                scope[name] = before
            elif signature is not None and signature not in ambiguous:
                # Share one merged fact only when every path agrees on aliasing.
                if signature not in records:
                    fields = {field: self.DYNAMIC_TYPE_CLASS() for field in before.fields}
                    records[signature] = self.INSTANCE_TYPE_CLASS(before.of, fields)
                scope[name] = records[signature]
            else:
                scope[name] = self.DYNAMIC_TYPE_CLASS()

    def walk_if(self, root):
        saved_scopes = self.scope_stack
        fallthrough = deepcopy(saved_scopes)
        paths = []
        self.scope_stack = fallthrough
        try:
            for branch in [root] + root.elif_branch.block:
                # A false earlier condition still runs and may mutate captures.
                self.walk_expression(branch.condition.root_expr)
                paths.append(self._walk_scoped_path(branch, check_condition=False))
            for branch in root.else_branch.block:
                paths.append(self._walk_scoped_path(branch, check_condition=False))
            paths.append(fallthrough)
        finally:
            self.scope_stack = saved_scopes
        self._merge_control_paths(paths)

    def walk_elif(self, root):
        self._merge_control_paths([self._walk_scoped_path(root)])

    def walk_else(self, root):
        self._merge_control_paths([self._walk_scoped_path(root)])

    def walk_for(self, root):
        # The bound is an expression too: validate it before binding the loop variable.
        self.walk_expression(root.bound.root_expr)
        self.loop_depth += 1
        try:
            path = self._walk_scoped_path(root, loop_target=root.variable)
        finally:
            self.loop_depth -= 1
        self._merge_control_paths([path])

    def walk_while(self, root):
        self.loop_depth += 1
        try:
            path = self._walk_scoped_path(root)
        finally:
            self.loop_depth -= 1
        self._merge_control_paths([path])

    def walk_break(self, root):
        if self.loop_depth == 0:
            raise SemanticError(
                self.file,
                "cannot break outside of loop scope",
                root.meta_data.line,
                root.meta_data.column_start,
                root.meta_data.column_end,
            )

    def walk_continue(self, root):
        if self.loop_depth == 0:
            raise SemanticError(
                self.file,
                "cannot continue outside of loop scope",
                root.meta_data.line,
                root.meta_data.column_start,
                root.meta_data.column_end,
            )

    def walk_return(self, root):
        if not self.func_depth:
            raise SemanticError(
                self.file,
                "cannot return outside of function scope",
                root.meta_data.line,
                root.meta_data.column_start,
                root.meta_data.column_end,
            )
        if root.expression:
            self.walk_expression(root.expression.root_expr)

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

    def search_for_var(self, name):
        if type(name) is self.IDENTIFIER_NODE_CLASS:
            name = name.value

        for scope in reversed(self.scope_stack):
            if name in scope:
                return scope[name]
        return ""

    def _error(self, message, node):
        metadata = getattr(node, "meta_data", None) or (node if hasattr(node, "line") else None)
        raise SemanticError(
            self.file,
            message,
            metadata.line if metadata else 1,
            metadata.column_start if metadata else 1,
            metadata.column_end if metadata else 2,
        )

    def _infer_binary_type(self, root, left, right):
        dynamic = self.DYNAMIC_TYPE_CLASS
        lt, rt, op = type(left), type(right), root.op
        numeric = (self.NUMBER_TYPE_CLASS, self.BOOL_TYPE_CLASS, self.NONE_TYPE_CLASS)
        if dynamic in (lt, rt) or op in (self.T_AND_ENUM_VAL, self.T_OR_ENUM_VAL):
            return dynamic()
        set_types = (self.SET_TYPE_CLASS, self.FROZEN_SET_TYPE_CLASS)
        if (
            lt in set_types and rt in set_types
            and op in (self.T_PLUS_ENUM_VAL, self.T_MINUS_ENUM_VAL)
        ):
            return lt(None)
        if op == self.T_IN_ENUM_VAL:
            containers = (
                self.ARRAY_TYPE_CLASS,
                self.STRING_TYPE_CLASS,
                self.SET_TYPE_CLASS,
                self.FROZEN_SET_TYPE_CLASS,
                self.DICT_TYPE_CLASS,
            )
            if rt not in containers or (rt is self.STRING_TYPE_CLASS and lt is not rt):
                self._error(operator_message(op, left, right), root)
            return self.BOOL_TYPE_CLASS(None)
        if op not in self.ARITH_OPS:
            return self.BOOL_TYPE_CLASS(None)
        if lt in numeric and rt in numeric:
            return self.NUMBER_TYPE_CLASS(None)
        if lt is rt:
            if lt is self.STRING_TYPE_CLASS and op == self.T_SLASH_ENUM_VAL:
                return self.ARRAY_TYPE_CLASS(None)
            if lt in (
                self.STRING_TYPE_CLASS,
                self.ARRAY_TYPE_CLASS,
                self.SET_TYPE_CLASS,
                self.FROZEN_SET_TYPE_CLASS,
                self.DICT_TYPE_CLASS,
            ):
                return lt(None)
            # Unsupported same-type operations receive a runtime diagnostic.
            return dynamic()
        norm_left = self.NUMBER_TYPE_CLASS if lt in numeric else lt
        norm_right = self.NUMBER_TYPE_CLASS if rt in numeric else rt
        result = self.BIN_OP_DIFFERENT_RULES.get((norm_left, norm_right, op))
        if result is None:
            self._error(operator_message(op, left, right), root)
        return result(None)

    def _index_type(self, base, index, root, position=0):
        typ = type(base)
        metadata = index_location(root, position)
        level = position + 1
        if type(index) is self.SLICE_TYPE_CLASS:
            if typ is self.DYNAMIC_TYPE_CLASS:
                return self.DYNAMIC_TYPE_CLASS()
            if typ not in (self.ARRAY_TYPE_CLASS, self.STRING_TYPE_CLASS):
                self._error(
                    f"slicing requires an array or string at level {level} (got {type_name(base)})",
                    metadata,
                )
            result_type = (
                self.ARRAY_TYPE_CLASS if typ is self.ARRAY_TYPE_CLASS else self.STRING_TYPE_CLASS
            )
            value = None
            if base.value is not None and index.value is not None:
                value = base.value[index.value]
            return result_type(value)
        if typ is self.DYNAMIC_TYPE_CLASS:
            return self.DYNAMIC_TYPE_CLASS()
        if typ is self.DICT_TYPE_CLASS:
            return self.DYNAMIC_TYPE_CLASS()
        if typ not in (self.ARRAY_TYPE_CLASS, self.STRING_TYPE_CLASS):
            self._error(nonindexable_message(base, level), metadata)
        if type(index) not in (
            self.NUMBER_TYPE_CLASS,
            self.BOOL_TYPE_CLASS,
            self.NONE_TYPE_CLASS,
            self.DYNAMIC_TYPE_CLASS,
        ):
            self._error(
                f"{type_name(base)} index at level {level} must be an integer "
                f"(got {type_name(index)})", metadata,
            )
        if base.value is None or index.value is None:
            return self.DYNAMIC_TYPE_CLASS()
        try:
            value = base.value[index.value]
        except (IndexError, TypeError, KeyError) as error:
            self._error(index_error_message(error, base.value, index.value, level), metadata)
        return self.STRING_TYPE_CLASS(value) if typ is self.STRING_TYPE_CLASS else value

    def _field_type(self, base, name, root):
        if type(base) is self.DYNAMIC_TYPE_CLASS:
            return self.DYNAMIC_TYPE_CLASS()
        if type(base) is not self.INSTANCE_TYPE_CLASS or name not in base.fields:
            self._error(field_error_message(base, name), root)
        return base.fields[name]

    def _resolve_type_target(self, target, *, require_existing=False):
        """Return the current fact and a writer for the same abstract location."""
        typ = type(target)
        if typ is self.IDENTIFIER_NODE_CLASS:
            for frame in reversed(self.scope_stack):
                if target.value in frame:
                    return (
                        frame[target.value],
                        lambda value, frame=frame: frame.__setitem__(target.value, value),
                    )
            if require_existing:
                self._error("variable not initialized", target)
            frame = self.scope_stack[-1]
            return self.DYNAMIC_TYPE_CLASS(), lambda value: frame.__setitem__(target.value, value)
        if typ is self.FIELD_ACCESS_NODE_CLASS:
            base = self.walk_expression(target.base)
            for position, name in enumerate(target.field[:-1]):
                base = self._field_type(base, name, field_location(target, position))
            current = self._field_type(
                base, target.field[-1], field_location(target, len(target.field) - 1)
            )
            if type(base) is self.INSTANCE_TYPE_CLASS:
                return current, lambda value: base.fields.__setitem__(target.field[-1], value)
            return current, lambda _value: self._invalidate_mutable_facts()
        if typ is self.INDEX_NODE_CLASS:
            base = self.walk_expression(target.base)
            for position, part in enumerate(target.index[:-1]):
                index = self.walk_expression(part.root_expr)
                base = self._index_type(base, index, target, position)
            index = self.walk_expression(target.index[-1].root_expr)
            position = len(target.index) - 1
            current = self._index_type(base, index, target, position)
            metadata = index_location(target, position)

            def update(value):
                if type(index) is self.SLICE_TYPE_CLASS:
                    if type(base) is self.STRING_TYPE_CLASS:
                        self._error(
                            "slice assignment requires an array target; strings are immutable",
                            metadata,
                        )
                    if type(value) not in (self.ARRAY_TYPE_CLASS, self.DYNAMIC_TYPE_CLASS):
                        self._error(
                            f"slice assignment requires an array value (got {type_name(value)})",
                            metadata,
                        )
                    if type(base) is self.DYNAMIC_TYPE_CLASS:
                        self._invalidate_mutable_facts()
                    elif type(base) is self.ARRAY_TYPE_CLASS:
                        if (
                            base.value is not None
                            and index.value is not None
                            and type(value) is self.ARRAY_TYPE_CLASS
                            and value.value is not None
                        ):
                            try:
                                base.value[index.value] = list(value.value)
                            except ValueError as error:
                                self._error(
                                    index_error_message(
                                        error, base.value, index.value, position + 1,
                                        writing=True, value=value.value,
                                    ), metadata,
                                )
                        else:
                            base.value = None
                    return
                if type(base) is self.ARRAY_TYPE_CLASS:
                    if base.value is not None and index.value is not None:
                        base.value[index.value] = value
                    else:
                        base.value = None
                elif type(base) is self.DICT_TYPE_CLASS:
                    base.value = None
                elif type(base) is self.DYNAMIC_TYPE_CLASS:
                    self._invalidate_mutable_facts()

            return current, update
        self._error("invalid assignment target", target)

    def walk_assignments(self, root):
        if (
            root.op == self.T_ASSIGN_ENUM_VAL
            and type(root.left_hand) is self.IDENTIFIER_NODE_CLASS
            and type(root.right_hand.root_expr) is self.FUNCTION_NODE_CLASS
        ):
            self._function_type(root.right_hand.root_expr, binding_name=root.left_hand.value)
            return
        self._walk_assignment(
            root.left_hand,
            root.op,
            root,
            lambda: self.walk_expression(root.right_hand.root_expr),
        )

    def _walk_assignment(self, left_hand, op, location, evaluate_rhs):
        """Share assignment binding with loops while preserving RHS evaluation order."""
        compound = op != self.T_ASSIGN_ENUM_VAL
        operation = self.BIN_OP_NODE_CLASS(
            left=None,
            op=self.ASSIGNMENT_TO_NORMAL.get(op, op),
            right=None,
            meta_data=location.meta_data,
        )

        def assign(target, value):
            if type(target) is self.ARRAY_LITERAL_NODE_CLASS:
                typ = type(value)
                if typ not in (self.ARRAY_TYPE_CLASS, self.DYNAMIC_TYPE_CLASS):
                    self._error("multi-variable assignment requires an array", location)
                items = value.value if typ is self.ARRAY_TYPE_CLASS else None
                if items is not None and len(items) < len(target.elements):
                    self._error("not enough values to unpack", location)
                for index, element in enumerate(target.elements):
                    items = value.value if typ is self.ARRAY_TYPE_CLASS else None
                    item = items[index] if items is not None else self.DYNAMIC_TYPE_CLASS()
                    assign(element.root_expr, item)
                return
            old, write = self._resolve_type_target(target, require_existing=compound)
            write(self._infer_binary_type(operation, old, value) if compound else value)

        if compound and type(left_hand) is not self.ARRAY_LITERAL_NODE_CLASS:
            old, write = self._resolve_type_target(left_hand, require_existing=True)
            value = evaluate_rhs()
            write(self._infer_binary_type(operation, old, value))
        else:
            assign(left_hand, evaluate_rhs())

    def _invalidate_mutable_facts(self, facts=None):
        if facts is None:
            facts = (value for scope in self.scope_stack for value in scope.values())
        pending = list(facts)
        seen = set()
        while pending:
            value = pending.pop()
            if id(value) in seen:
                continue
            seen.add(id(value))
            if type(value) is self.ARRAY_TYPE_CLASS:
                if value.value is not None:
                    pending.extend(value.value)
                value.value = None
            elif type(value) is self.INSTANCE_TYPE_CLASS:
                pending.extend(value.fields.values())
                for name in value.fields:
                    value.fields[name] = self.DYNAMIC_TYPE_CLASS()
            elif type(value) in (
                self.SET_TYPE_CLASS, self.FROZEN_SET_TYPE_CLASS, self.DICT_TYPE_CLASS,
            ):
                if value.value is not None:
                    pending.extend(value.value)
                value.value = None

    def _invalidate_call_facts(self):
        """An unknown user call may rebind captures and mutate reachable objects."""
        self._invalidate_mutable_facts()
        for scope in self.scope_stack:
            for name in scope:
                scope[name] = self.DYNAMIC_TYPE_CLASS()

    def _infer_call_type(self, root, callee, arguments):
        typ = type(callee)
        keywords = root.keyword_names
        if keywords and typ not in (self.DYNAMIC_TYPE_CLASS, self.FUNCTION_TYPE_CLASS, BuiltinType):
            self._error("named arguments require a function with declared parameters", root)
        if typ is self.FUNCTION_TYPE_CLASS:
            if callee.parameters is None:
                if keywords:
                    self._error("variadic functions accept positional arguments only", root)
            else:
                try:
                    bind_arguments(
                        callee.parameters, arguments, keywords, variadic_name=callee.variadic_name
                    )
                except ValueError as error:
                    self._error(str(error), root)
        if typ is self.DATA_CLASS_TYPE_CLASS:
            if len(arguments) > len(callee.fields):
                self._error(
                    f"too many constructor arguments (expected at most {len(callee.fields)}, "
                    f"got {len(arguments)})", root,
                )
            fields = {
                name: arguments[index] if index < len(arguments) else self.DYNAMIC_TYPE_CLASS()
                for index, name in enumerate(callee.fields)
            }
            return self.INSTANCE_TYPE_CLASS(of=callee, fields=fields)
        if typ is BuiltinType:
            return infer_builtin(self, root, callee.name, arguments)
        if typ not in (self.DYNAMIC_TYPE_CLASS, self.FUNCTION_TYPE_CLASS):
            self._error(f"attempt to call a non-function (got {type_name(callee)})", root)
        self._invalidate_call_facts()
        return self.DYNAMIC_TYPE_CLASS()

    def walk_expression(self, root):
        """Infer facts with an explicit traversal stack, including deep flat trees."""
        tasks = [("eval", root)]
        values = []
        while tasks:
            task = tasks.pop()
            tag, node = task[:2]
            if tag == "eval":
                typ = type(node)
                if typ is self.EXPRESSION_NODE_CLASS:
                    tasks.append(("eval", node.root_expr))
                elif typ is self.FUNCTION_NODE_CLASS:
                    values.append(self._function_type(node))
                elif typ is self.SLICE_NODE_CLASS:
                    parts = (node.start, node.stop, node.step)
                    tasks.append(("slice", node, sum(part is not None for part in parts)))
                    tasks.extend(
                        ("eval", part.root_expr) for part in reversed(parts) if part is not None
                    )
                elif typ is self.INTERPOLATED_STRING_NODE_CLASS:
                    fields = [part for part in node.parts if not isinstance(part, str)]
                    tasks.append(("interpolation", node, len(fields)))
                    tasks.extend(("eval", part.root_expr) for part in reversed(fields))
                elif typ is self.DYNAMIC_TYPE_CLASS:
                    values.append(node)
                elif typ in self.LITERALS:
                    value = 0 if typ is self.NONE_LITERAL_NODE_CLASS else node.value
                    values.append(self.LITERALS[typ](value))
                elif typ is self.IDENTIFIER_NODE_CLASS:
                    value = self.search_for_var(node.value)
                    if not value:
                        self._error(f"variable not initialized '{node.value}'", node)
                    values.append(value)
                elif typ is self.BIN_OP_NODE_CLASS:
                    tasks.extend((("binary", node), ("eval", node.right), ("eval", node.left)))
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
                    self._error("invalid expression node", node)
            elif tag == "slice":
                count = task[2]
                supplied = values[-count:] if count else []
                if count:
                    del values[-count:]
                iterator = iter(supplied)
                bounds = []
                known = True
                for role, part in zip(
                    ("start", "stop", "step"), (node.start, node.stop, node.step), strict=True
                ):
                    if part is None:
                        bounds.append(None)
                        continue
                    fact = next(iterator)
                    if type(fact) not in (
                        self.NUMBER_TYPE_CLASS,
                        self.BOOL_TYPE_CLASS,
                        self.NONE_TYPE_CLASS,
                        self.DYNAMIC_TYPE_CLASS,
                    ):
                        self._error(
                            f"slice {role} must be an integer (got {type_name(fact)})",
                            expression_location(part, node.meta_data),
                        )
                    if fact.value is None:
                        known = False
                    elif not isinstance(fact.value, int):
                        self._error(
                            f"slice {role} must be an integer (got {type_name(fact)})",
                            expression_location(part, node.meta_data),
                        )
                    bounds.append(fact.value)
                if node.step is not None and bounds[2] == 0:
                    self._error(
                        "slice step cannot be zero", expression_location(node.step, node.meta_data)
                    )
                values.append(self.SLICE_TYPE_CLASS(slice(*bounds) if known else None))
            elif tag == "interpolation":
                count = task[2]
                if count:
                    del values[-count:]
                values.append(self.STRING_TYPE_CLASS(None))
            elif tag == "binary":
                right, left = values.pop(), values.pop()
                values.append(self._infer_binary_type(node, left, right))
            elif tag == "unary":
                operand = values.pop()
                if node.op == self.T_NEGATE_ENUM_VAL:
                    value = self.BOOL_TYPE_CLASS(None)
                elif type(operand) is self.DYNAMIC_TYPE_CLASS:
                    value = self.DYNAMIC_TYPE_CLASS()
                elif type(operand) in (
                    self.NUMBER_TYPE_CLASS,
                    self.BOOL_TYPE_CLASS,
                    self.NONE_TYPE_CLASS,
                ):
                    value = self.NUMBER_TYPE_CLASS(None)
                else:
                    self._error(
                        f"unary '{node.meta_data.value}' requires a number "
                        f"(got {type_name(operand)})", node,
                    )
                values.append(value)
            elif tag == "array":
                count = task[2]
                result = values[-count:] if count else []
                if count:
                    del values[-count:]
                values.append(self.ARRAY_TYPE_CLASS(result))
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
                values.append(self._index_type(task[3], values.pop(), node, task[2]))
                tasks.append(("index", node, task[2] + 1))
            elif tag == "field":
                base = values.pop()
                for position, name in enumerate(node.field):
                    base = self._field_type(base, name, field_location(node, position))
                values.append(base)
            elif tag == "callee":
                callee = values.pop()
                tasks.append(("call", node, callee, len(node.args)))
                tasks.extend(("eval", item.root_expr) for item in reversed(node.args))
            elif tag == "call":
                count = task[3]
                arguments = values[-count:] if count else []
                if count:
                    del values[-count:]
                values.append(self._infer_call_type(node, task[2], arguments))
        return values.pop()
