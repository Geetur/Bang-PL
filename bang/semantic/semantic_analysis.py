# ONLY APPLIES TO STATICALLY KNOWABLE THINGS
# after this pass we are every variable is guaranteed to be defined before use;
# every break, continue, return, is guaranteed to bee associated with a loop/function;
# all statically known indexes are guaranteed to be numbers;
# all bin ops and unary ops are guaranteed to be valid if statically known
# the majority of errors that can be statically determined are determined.

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
    NONE_LITERAL_NODE_CLASS,
    RETURN_NODE_CLASS,
    STRING_LITERAL_NODE_CLASS,
    UNARY_OP_NODE_CLASS,
    WHILE_NODE_CLASS,
)
from bang.semantic.semantic_nodes import (
    ARRAY_TYPE_CLASS,
    BOOL_TYPE_CLASS,
    DATA_CLASS_TYPE_CLASS,
    DICT_TYPE_CLASS,
    DYNAMIC_TYPE_CLASS,
    FUNCTION_TYPE_CLASS,
    INSTANCE_TYPE_CLASS,
    NONE_TYPE_CLASS,
    NUMBER_TYPE_CLASS,
    SET_TYPE_CLASS,
    STRING_TYPE_CLASS,
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
            f"[SemanticError] Line {self.row + 1}, Column {self.start}-{self.end}:\n"
            f"{error_line.rstrip()}\n"
            f"{pointers}\n"
            f"{self.msg}"
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

    BUILT_IN_FUNCTIONS = {
        "print": FUNCTION_TYPE_CLASS,
        "len": FUNCTION_TYPE_CLASS,
        "sum": FUNCTION_TYPE_CLASS,
        "min": FUNCTION_TYPE_CLASS,
        "max": FUNCTION_TYPE_CLASS,
        "sort": FUNCTION_TYPE_CLASS,
        "set": SET_TYPE_CLASS,
        "dict": DICT_TYPE_CLASS,
        "range": FUNCTION_TYPE_CLASS,
    }

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

        self.scope_stack[0].update(
            {name: typ(value=None) for name, typ in self.BUILT_IN_FUNCTIONS.items()}
        )

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
            self.walk_construct(construct)

    # could probably use this walk_construct more
    # typically but its clearer to just call the specific expression
    # in some cases although this could change
    def walk_construct(self, root):
        handler = self.CONSTRUCTS_TO_WALK[type(root)]
        return handler(root)

    def walk_function(self, root):
        function_name = root.name
        args_name = root.arg_list_name
        # its really important to initalize the function outside of its bodys scope
        #
        self.initalize_var(function_name, FUNCTION_TYPE_CLASS(value=root.body))

        self.func_depth += 1
        self.scope_stack.append({})
        self.initalize_var(args_name, DYNAMIC_TYPE_CLASS())

        self.walk_block(root.body)
        self.scope_stack.pop()
        self.func_depth -= 1

    def walk_dataclass(self, root):
        dataclass_name = root.name
        # removing duplicate names
        seen = set()
        dataclass_fields = [f for f in root.fields if not (f in seen or seen.add(f))]
        self.initalize_var(dataclass_name, DATA_CLASS_TYPE_CLASS(fields=dataclass_fields))

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
        right_hand_type = DYNAMIC_TYPE_CLASS()
        if type(right_hand_type) in (NONE_TYPE_CLASS,):
            raise SemanticError(
                self.file,
                "For loop bound must be an array, identifier, or number",
                root.meta_data.line,
                root.meta_data.column_start,
                root.meta_data.column_end,
            )
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
        if type(name) is IDENTIFIER_NODE_CLASS:
            name = name.value

        for scope in reversed(self.scope_stack):
            if name in scope:
                return scope[name]
        return ""

    def walk_assignments(self, root):
        DYNAMIC_TYPE_CLASS = self.DYNAMIC_TYPE_CLASS
        NUMBER_TYPE_CLASS = self.NUMBER_TYPE_CLASS
        BOOL_TYPE_CLASS = self.BOOL_TYPE_CLASS

        ARITH_ASSIGNMENTS = self.ARITH_ASSIGNMENTS
        ASSIGNMENTS_TO_NORMAL = self.ASSIGNMENT_TO_NORMAL
        BIN_OP_DIFFERENT_RULES = self.BIN_OP_DIFFERENT_RULES

        def walk_assignment_typical(left_hand, op_type_id, right_hand):
            left_hand_name = left_hand.value
            left_hand_type = self.search_for_var(left_hand_name)
            type_left_hand_type = type(left_hand_type)
            type_right_hand = type(right_hand)
            if (
                type_left_hand_type is not DYNAMIC_TYPE_CLASS
                and op_type_id in ARITH_ASSIGNMENTS
                and type_right_hand is not DYNAMIC_TYPE_CLASS
            ):
                op_type_id = ASSIGNMENTS_TO_NORMAL[op_type_id]
                if not left_hand_type:
                    raise SemanticError(
                        self.file,
                        "variable not initialized",
                        root.meta_data.line,
                        root.meta_data.column_start,
                        root.meta_data.column_end,
                    )
                # is it the same type?
                if not (
                    (
                        type_right_hand in (NUMBER_TYPE_CLASS, BOOL_TYPE_CLASS)
                        and type_left_hand_type in (NUMBER_TYPE_CLASS, BOOL_TYPE_CLASS)
                    )
                    or type_left_hand_type is type_right_hand
                ):
                    # does it adhere to different type operation rules?
                    if (
                        type_left_hand_type,
                        type_right_hand,
                        op_type_id,
                    ) not in BIN_OP_DIFFERENT_RULES:
                        raise SemanticError(
                            self.file,
                            "Invalid operation",
                            root.meta_data.line,
                            root.meta_data.column_start,
                            root.meta_data.column_end,
                        )
            self.initalize_var(left_hand_name, right_hand)

        def walk_assignment_index(left_hand, op_type_id, right_hand):
            left_hand_type = self.walk_expression(left_hand)
            type_left_hand_type = type(left_hand_type)
            type_right_hand = type(right_hand)
            if (
                type_left_hand_type is not DYNAMIC_TYPE_CLASS
                and type_right_hand is not DYNAMIC_TYPE_CLASS
            ):
                if not left_hand_type:
                    raise SemanticError(
                        self.file,
                        "variable not initialized",
                        root.meta_data.line,
                        root.meta_data.column_start,
                        root.meta_data.column_end,
                    )
                if op_type_id in ARITH_ASSIGNMENTS:
                    op_type_id = ASSIGNMENTS_TO_NORMAL[op_type_id]
                    if not (
                        (
                            type_right_hand in (NUMBER_TYPE_CLASS, BOOL_TYPE_CLASS)
                            and type_left_hand_type in (NUMBER_TYPE_CLASS, BOOL_TYPE_CLASS)
                        )
                        or type_left_hand_type is type_right_hand
                    ):
                        if (
                            type_left_hand_type,
                            type_right_hand,
                            op_type_id,
                        ) not in BIN_OP_DIFFERENT_RULES:
                            raise SemanticError(
                                self.file,
                                "Invalid operation",
                                root.meta_data.line,
                                root.meta_data.column_start,
                                root.meta_data.column_end,
                            )

        def walk_assignment_field_access(left_hand, op_type_id, right_hand):
            INSTANCE_TYPE_CLASS = self.INSTANCE_TYPE_CLASS
            base_type = self.walk_expression(left_hand.base)
            fields_chain = left_hand.field
            type_right_hand = type(right_hand)
            for name in fields_chain[:-1]:
                type_base_type = type(base_type)
                if type_base_type is DYNAMIC_TYPE_CLASS:
                    return
                if type_base_type is not INSTANCE_TYPE_CLASS:
                    raise SemanticError(
                        self.file,
                        "field access only performable on instances of classes",
                        left_hand.meta_data.line,
                        left_hand.meta_data.column_start,
                        left_hand.meta_data.column_end,
                    )
                derived_class = self.search_for_var(base_type.of)
                type_derived_class = type(derived_class)
                if type_derived_class is DYNAMIC_TYPE_CLASS:
                    return
                if type_derived_class is not DATA_CLASS_TYPE_CLASS:
                    raise SemanticError(
                        self.file,
                        "field access is only performable on instances of classes",
                        left_hand.meta_data.line,
                        left_hand.meta_data.column_start,
                        left_hand.meta_data.column_end,
                    )
                if name not in derived_class.fields:
                    raise SemanticError(
                        self.file,
                        "field name wasn't included in the definition of "
                        "the instance's corresponding class",
                        left_hand.meta_data.line,
                        left_hand.meta_data.column_start,
                        left_hand.meta_data.column_end,
                    )
                base_type = base_type.fields[name]
            type_base_type = type(base_type)
            if type_base_type is DYNAMIC_TYPE_CLASS:
                return
            if type_base_type is not INSTANCE_TYPE_CLASS:
                raise SemanticError(
                    self.file,
                    "field access is only performable on instances of classes",
                    left_hand.meta_data.line,
                    left_hand.meta_data.column_start,
                    left_hand.meta_data.column_end,
                )

            parent_instance_type = base_type
            final_field = fields_chain[-1]
            derived_class = self.search_for_var(parent_instance_type.of)
            type_derived_class = type(derived_class)
            if type_derived_class is DYNAMIC_TYPE_CLASS:
                return
            if (
                type_derived_class is not DATA_CLASS_TYPE_CLASS
                or final_field not in derived_class.fields
            ):
                raise SemanticError(
                    self.file,
                    "field name wasn't included in the definition "
                    "of the instance's corresponding class",
                    left_hand.meta_data.line,
                    left_hand.meta_data.column_start,
                    left_hand.meta_data.column_end,
                )

            current_field_type = parent_instance_type.fields[final_field]
            type_current_field_type = type(current_field_type)
            if (
                type_current_field_type is not DYNAMIC_TYPE_CLASS
                and type_right_hand is not DYNAMIC_TYPE_CLASS
                and op_type_id in ARITH_ASSIGNMENTS
            ):
                op_norm = ASSIGNMENTS_TO_NORMAL[op_type_id]
                same_num_bool = type_right_hand in (
                    NUMBER_TYPE_CLASS,
                    BOOL_TYPE_CLASS,
                ) and type_current_field_type in (
                    NUMBER_TYPE_CLASS,
                    BOOL_TYPE_CLASS,
                )
                if not (same_num_bool or type_current_field_type is type_right_hand):
                    if (
                        type_current_field_type,
                        type_right_hand,
                        op_norm,
                    ) not in BIN_OP_DIFFERENT_RULES:
                        raise SemanticError(
                            self.file,
                            "Invalid operation",
                            left_hand.meta_data.line,
                            left_hand.meta_data.column_start,
                            left_hand.meta_data.column_end,
                        )
            parent_instance_type.fields[final_field] = right_hand

        def walk_assignment_multi(left_hand, op_type_id, right_hand):
            type_right_hand = type(right_hand)
            right_hand_value = right_hand.value
            left_hand_elements = left_hand.elements
            len_left_hand_elements = len(left_hand_elements)
            if type_right_hand is not DYNAMIC_TYPE_CLASS:
                if type_right_hand is not ARRAY_TYPE_CLASS:
                    raise SemanticError(
                        self.file,
                        "multi-initialization requires right hand"
                        " to be dynamic type or static array type",
                        root.meta_data.line,
                        root.meta_data.column_start,
                        root.meta_data.column_end,
                    )
                if len_left_hand_elements > len(right_hand_value):
                    raise SemanticError(
                        self.file,
                        "multi-initialization requires right hand length "
                        "to be equal to or greater than left hand length",
                        root.meta_data.line,
                        root.meta_data.column_start,
                        root.meta_data.column_end,
                    )

                rhs_types = (
                    right_hand_value
                    if type_right_hand is ARRAY_TYPE_CLASS
                    else [DYNAMIC_TYPE_CLASS()] * len_left_hand_elements
                )

                dispatch = {
                    IDENTIFIER_NODE_CLASS: walk_assignment_typical,
                    INDEX_NODE_CLASS: walk_assignment_index,
                    ARRAY_LITERAL_NODE_CLASS: walk_assignment_multi,  # nested destructuring
                    FIELD_ACCESS_NODE_CLASS: walk_assignment_field_access,
                }

                for i, n in enumerate(left_hand_elements):
                    left_hand_node = n.root_expr
                    rhs_type = rhs_types[i] if i < len(rhs_types) else DYNAMIC_TYPE_CLASS
                    dispatch[type(left_hand_node)](left_hand_node, op_type_id, rhs_type)

        find_assignment_type = {
            IDENTIFIER_NODE_CLASS: walk_assignment_typical,
            INDEX_NODE_CLASS: walk_assignment_index,
            ARRAY_LITERAL_NODE_CLASS: walk_assignment_multi,
            FIELD_ACCESS_NODE_CLASS: walk_assignment_field_access,
        }
        root_left_hand = root.left_hand
        find_assignment_type[type(root_left_hand)](
            root_left_hand, root.op, self.walk_expression(root.right_hand.root_expr)
        )

    def walk_expression(self, root):
        DYNAMIC_TYPE_CLASS = self.DYNAMIC_TYPE_CLASS

        type_root = type(root)

        if type_root is EXPRESSION_NODE_CLASS:
            return self.walk_expression(root.root_expr)

        if type_root in self.LITERALS:
            actual_type = self.LITERALS[type_root]
            return actual_type(root.value)

        if type_root is DYNAMIC_TYPE_CLASS:
            return DYNAMIC_TYPE_CLASS()

        elif type_root is BIN_OP_NODE_CLASS:
            left = self.walk_expression(root.left)
            right = self.walk_expression(root.right)
            type_left = type(left)
            type_right = type(right)
            root_type_id = root.op

            if type_left is DYNAMIC_TYPE_CLASS or type_right is DYNAMIC_TYPE_CLASS:
                return DYNAMIC_TYPE_CLASS()

            if root_type_id == T_IN_ENUM_VAL:
                if type_right in (
                    ARRAY_TYPE_CLASS,
                    STRING_TYPE_CLASS,
                    SET_TYPE_CLASS,
                    DICT_TYPE_CLASS,
                ):
                    if not (type_left is not STRING_TYPE_CLASS and type_right is STRING_TYPE_CLASS):
                        return BOOL_TYPE_CLASS(value=None)
                raise SemanticError(
                    self.file,
                    f"in operator not supported between {type_left} and {type_right}",
                    root.meta_data.line,
                    root.meta_data.column_start,
                    root.meta_data.column_end,
                )

            if (
                not (
                    (
                        type_right in (NUMBER_TYPE_CLASS, BOOL_TYPE_CLASS)
                        and type_left in (NUMBER_TYPE_CLASS, BOOL_TYPE_CLASS)
                    )
                    or type_left is type_right
                )
            ) and root_type_id in self.ARITH_OPS:
                if (type_left, type_right, root_type_id) not in self.BIN_OP_DIFFERENT_RULES:
                    raise SemanticError(
                        self.file,
                        "Invalid operation",
                        root.meta_data.line,
                        root.meta_data.column_start,
                        root.meta_data.column_end,
                    )
                else:
                    return self.BIN_OP_DIFFERENT_RULES[(type_left, type_right, root_type_id)](
                        value=None
                    )

            # the value is none because we aren't evaluating
            # anything just determining its type
            # anythingt that requires binop to be evaluated to
            # throw an error will be a runtime error

            c = type_left if root_type_id in self.ARITH_OPS else BOOL_TYPE_CLASS
            return c(value=None)

        elif type_root is UNARY_OP_NODE_CLASS:
            root_type_id = root.op
            op = self.walk_expression(root.operand)
            type_op = type(op)

            if type_op is DYNAMIC_TYPE_CLASS:
                return DYNAMIC_TYPE_CLASS()

            if type_op not in self.ALLOWED_UNARY_OPS and root_type_id != T_NEGATE_ENUM_VAL:
                raise SemanticError(
                    self.file,
                    "Invalid operation",
                    root.meta_data.line,
                    root.meta_data.column_start,
                    root.meta_data.column_end,
                )

            # the value is none because we aren't evaluating
            # anything just determining its type
            # anythingt that requires binop to be evaluated to
            # throw an error will be a runtime error
            return (
                BOOL_TYPE_CLASS(value=None)
                if root_type_id == T_NEGATE_ENUM_VAL
                else NUMBER_TYPE_CLASS(value=None)
            )

        elif type_root is ARRAY_LITERAL_NODE_CLASS:
            checking_exprs = []
            for e in root.elements:
                typed_expression = (
                    self.walk_expression(e.root_expr)
                    if type(e) is EXPRESSION_NODE_CLASS
                    else self.walk_expression(e)
                )
                checking_exprs.append(typed_expression)

            return ARRAY_TYPE_CLASS(value=checking_exprs)

        elif type_root is INDEX_NODE_CLASS:
            base = self.walk_expression(root.base)
            type_base = type(base)
            base_value = base.value
            if type_base is DYNAMIC_TYPE_CLASS:
                return DYNAMIC_TYPE_CLASS()
            # notice the if base.value
            # remember that if it dosent have a value its not staically knowable
            # so we only throw an error ifs its knowable and an error
            # things that are errors after evaluation will be runtime errors

            # pretty sure from here down there is some
            # redundant code but it is only redundant, and working
            if base_value:
                if type_base not in (ARRAY_TYPE_CLASS, STRING_TYPE_CLASS, DICT_TYPE_CLASS):
                    raise SemanticError(
                        self.file,
                        f"object of {type_base} not indexable",
                        root.meta_data.line,
                        root.meta_data.column_start,
                        root.meta_data.column_end,
                    )

            indexes = []

            for idx in root.index:
                idx_type = self.walk_expression(idx.root_expr)
                if type_base in (ARRAY_TYPE_CLASS, STRING_TYPE_CLASS):
                    if type(idx_type) not in (
                        NUMBER_TYPE_CLASS,
                        BOOL_TYPE_CLASS,
                        DYNAMIC_TYPE_CLASS,
                    ):
                        raise SemanticError(
                            self.file,
                            f"Index must be number when base is type {type(base)}",
                            root.meta_data.line,
                            root.meta_data.column_start,
                            root.meta_data.column_end,
                        )
                indexes.append(idx_type)

            # if the base is unknowable statically than their is no point
            # to run over static indexes because we dont know the bounds of the base
            if not base_value or type_base is DICT_TYPE_CLASS:
                return DYNAMIC_TYPE_CLASS()

            for _pos, idx in enumerate(indexes):
                idx_value = idx.value
                if type_base not in (ARRAY_TYPE_CLASS, STRING_TYPE_CLASS):
                    raise SemanticError(
                        self.file,
                        "Index out of bounds",
                        root.meta_data.line,
                        root.meta_data.column_start,
                        root.meta_data.column_end,
                    )
                element_list = base_value

                # if the value is statically unknowable we cant continue iterating
                # through the indexes because we dont know where to nest into
                if idx_value is not None:
                    try:
                        base = element_list[idx_value]
                    except (IndexError, TypeError, KeyError):
                        raise SemanticError(
                            self.file,
                            "Index out of bounds",
                            root.meta_data.line,
                            root.meta_data.column_start,
                            root.meta_data.column_end,
                        ) from None

                else:
                    return DYNAMIC_TYPE_CLASS()

            return base

        elif type_root is IDENTIFIER_NODE_CLASS:
            # making sure each identifier is defined if its used in a given scope
            actual_type = self.search_for_var(root.value)
            if not actual_type:
                raise SemanticError(
                    self.file,
                    f"variable not initalized '{root.value}'",
                    root.meta_data.line,
                    root.meta_data.column_start,
                    root.meta_data.column_end,
                )
            return actual_type

        elif type_root is CALL_NODE_CLASS:
            # call functions that can be statically determined

            def walk_built_in_set(root):
                expected_return = []
                typed_args = [self.walk_expression(arg.root_expr) for arg in root.args]
                len_typed_args = len(typed_args)

                if not len_typed_args:
                    return SET_TYPE_CLASS(value=expected_return)
                typed_args_0 = typed_args[0]
                type_typed_args_0 = type(typed_args_0)

                if len_typed_args == 1:
                    if type_typed_args_0 is DYNAMIC_TYPE_CLASS:
                        return SET_TYPE_CLASS(value=expected_return)
                    elif type_typed_args_0 in (SET_TYPE_CLASS, ARRAY_TYPE_CLASS):
                        typed_args = typed_args_0.value
                        # need this is none check due to bin op/un op
                        # returning base_type(value=None)
                        if typed_args is None:
                            return SET_TYPE_CLASS(value=expected_return)

                for arg in typed_args:
                    if type(arg) in self.UNHASHABLE_TYPES:
                        raise SemanticError(
                            self.file,
                            f"set expects hashable types only, not {type(arg)}",
                            root.meta_data.line,
                            root.meta_data.column_start,
                            root.meta_data.column_end,
                        )
                    expected_return.append(arg)
                return SET_TYPE_CLASS(value=expected_return)

            def walk_built_in_dict(root):
                expected_return = []
                is_key = True
                typed_args = [self.walk_expression(arg.root_expr) for arg in root.args]
                len_typed_args = len(typed_args)

                if not len_typed_args:
                    return DICT_TYPE_CLASS(value=expected_return)

                typed_args_0 = typed_args[0]
                type_typed_args_0 = type(typed_args_0)

                if len_typed_args == 1:
                    if type_typed_args_0 is DYNAMIC_TYPE_CLASS:
                        return DICT_TYPE_CLASS(value=expected_return)
                    elif type_typed_args_0 in (SET_TYPE_CLASS, ARRAY_TYPE_CLASS):
                        typed_args = typed_args_0.value
                        if typed_args is None:
                            return DICT_TYPE_CLASS(value=expected_return)
                        len_typed_args = len(typed_args)

                if len_typed_args % 2 != 0:
                    raise SemanticError(
                        self.file,
                        f"'{root.name.value}' dict must be even; every key must have a value",
                        root.meta_data.line,
                        root.meta_data.column_start,
                        root.meta_data.column_end,
                    )
                for arg in typed_args:
                    if type(arg) in self.UNHASHABLE_TYPES and is_key:
                        raise SemanticError(
                            self.file,
                            f"'{root.name.value}' dict key expects hashable types only,"
                            f"not {type(arg)}",
                            root.meta_data.line,
                            root.meta_data.column_start,
                            root.meta_data.column_end,
                        )
                    is_key = not is_key
                    expected_return.append(arg)
                return DICT_TYPE_CLASS(value=expected_return)

            built_in_to_walk = {
                "set": walk_built_in_set,
                "dict": walk_built_in_dict,
            }

            root_args = root.args
            root_name = root.name
            type_root_name = type(root_name)
            len_root_args = len(root_args)

            if type_root_name is not IDENTIFIER_NODE_CLASS:
                return DYNAMIC_TYPE_CLASS()

            callee_type = self.search_for_var(root_name)
            type_callee_type = type(callee_type)

            if type_callee_type is DYNAMIC_TYPE_CLASS:
                return DYNAMIC_TYPE_CLASS()

            if type_callee_type is DATA_CLASS_TYPE_CLASS:
                if len_root_args > len(callee_type.fields):
                    raise SemanticError(
                        self.file,
                        "more arguments than dataclass paramaters",
                        root.meta_data.line,
                        root.meta_data.column_start,
                        root.meta_data.column_end,
                    )
                fields = {}
                for idx, field in enumerate(callee_type.fields):
                    fields[field] = DYNAMIC_TYPE_CLASS()
                    if len_root_args > idx:
                        fields[field] = self.walk_expression(root_args[idx].root_expr)

                return INSTANCE_TYPE_CLASS(of=root.name.value, fields=fields)

            if not callee_type:
                raise SemanticError(
                    self.file,
                    f"function not intialized '{root.name.value}'",
                    root.meta_data.line,
                    root.meta_data.column_start,
                    root.meta_data.column_end,
                )

            if type_callee_type not in (FUNCTION_TYPE_CLASS, SET_TYPE_CLASS, DICT_TYPE_CLASS):
                raise SemanticError(
                    self.file,
                    f"attempt to call non-function '{root.name.value}'",
                    root.meta_data.line,
                    root.meta_data.column_start,
                    root.meta_data.column_end,
                )
            # the and allows user shadowing without interfering
            # if a decision is made to really add to the semantic analysis
            # with type checking for every built in function, this will change
            # from hardcode to like self.builtintypes or something
            root_name_value = root.name.value
            if root_name_value in built_in_to_walk and type_callee_type in (
                SET_TYPE_CLASS,
                DICT_TYPE_CLASS,
            ):
                return built_in_to_walk[root_name_value](root)

            # Analyse each argument expression normally.
            for arg in root_args:
                self.walk_expression(arg.root_expr)

            return DYNAMIC_TYPE_CLASS()

        elif type(root) is FIELD_ACCESS_NODE_CLASS:
            # to do
            base = self.walk_expression(root.base)

            fields = root.field

            for field_name in fields:
                type_base = type(base)
                if type_base is DYNAMIC_TYPE_CLASS:
                    return DYNAMIC_TYPE_CLASS()
                if type_base is not INSTANCE_TYPE_CLASS:
                    raise SemanticError(
                        self.file,
                        "field access is only performable on instances of classes",
                        root.meta_data.line,
                        root.meta_data.column_start,
                        root.meta_data.column_end,
                    )
                derived_class = self.search_for_var(base.of)
                type_derived_class = type(derived_class)
                if type_derived_class is DYNAMIC_TYPE_CLASS:
                    return DYNAMIC_TYPE_CLASS()
                if type_derived_class is not DATA_CLASS_TYPE_CLASS:
                    raise SemanticError(
                        self.file,
                        "field access is only performable on instances of classes",
                        root.meta_data.line,
                        root.meta_data.column_start,
                        root.meta_data.column_end,
                    )
                if field_name not in derived_class.fields:
                    raise SemanticError(
                        self.file,
                        "field name wasn't included in the definition of "
                        "the instance's corresponding class",
                        root.meta_data.line,
                        root.meta_data.column_start,
                        root.meta_data.column_end,
                    )
                field_type = base.fields[field_name]
                base = field_type
            return base
