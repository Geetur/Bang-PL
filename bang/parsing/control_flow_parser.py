"""Group statement ASTs into blocks, with one end per conditional chain."""

from bang.parsing.expression_parser import ParserError
from bang.parsing.parser_nodes import (
    ELIF_NODE_CLASS,
    ELSE_NODE_CLASS,
    END_NODE_CLASS,
    FOR_NODE_CLASS,
    FUNCTION_NODE_CLASS,
    IF_NODE_CLASS,
    RETURN_NODE_CLASS,
    WHILE_NODE_CLASS,
)


class ControlFlowParser:
    MAX_BLOCK_DEPTH = 64

    ELIF_NODE_CLASS = ELIF_NODE_CLASS
    ELSE_NODE_CLASS = ELSE_NODE_CLASS
    END_NODE_CLASS = END_NODE_CLASS
    FOR_NODE_CLASS = FOR_NODE_CLASS
    FUNCTION_NODE_CLASS = FUNCTION_NODE_CLASS
    IF_NODE_CLASS = IF_NODE_CLASS
    RETURN_NODE_CLASS = RETURN_NODE_CLASS
    WHILE_NODE_CLASS = WHILE_NODE_CLASS

    CONTROL_FLOW_NODES = (
        IF_NODE_CLASS,
        FOR_NODE_CLASS,
        WHILE_NODE_CLASS,
        FUNCTION_NODE_CLASS,
    )

    DEPENDANT_NODES = (ELIF_NODE_CLASS, ELSE_NODE_CLASS)
    BLOCK_NAMES = {
        IF_NODE_CLASS: "if",
        FOR_NODE_CLASS: "for",
        WHILE_NODE_CLASS: "while",
        FUNCTION_NODE_CLASS: "fn",
    }

    def __init__(self, file, expression_nodes):
        self.file = file
        self.expression_nodes = expression_nodes
        self.post_blockenize = []

    def _error(self, node, message):
        return ParserError(
            self.file,
            message,
            node.meta_data.line,
            node.meta_data.column_start,
            node.meta_data.column_end,
        )

    def blockenize(self):
        cls = self.__class__
        # Each frame holds the block owner and the body currently receiving statements.
        # elif/else select another body of the same if; they never open a new frame.
        stack = []

        for node in self.expression_nodes:
            type_node = type(node)
            if type_node in cls.DEPENDANT_NODES:
                branch_name = node.meta_data.value
                if not stack:
                    raise self._error(node, f"'{branch_name}' has no matching open 'if'")
                owner, _ = stack[-1]
                if type(owner) is not cls.IF_NODE_CLASS:
                    raise self._error(
                        node,
                        f"'{branch_name}' requires the current open block to be 'if'; "
                        f"close the '{cls.BLOCK_NAMES[type(owner)]}' block first",
                    )
                if owner.else_branch.block:
                    raise self._error(node, "else must be the last branch and may appear only once")
                branches = (
                    owner.elif_branch if type_node is cls.ELIF_NODE_CLASS else owner.else_branch
                )
                branches.block.append(node)
                stack[-1] = (owner, node.body)
                continue

            if type_node in cls.CONTROL_FLOW_NODES:
                if len(stack) >= self.MAX_BLOCK_DEPTH:
                    raise self._error(
                        node,
                        f"block nesting exceeds the limit of {self.MAX_BLOCK_DEPTH}",
                    )
                stack.append((node, node.body))
                continue

            if type_node is cls.END_NODE_CLASS:
                if not stack:
                    raise self._error(node, "'end' has no matching open block")
                node, _ = stack.pop()
            elif type_node is cls.RETURN_NODE_CLASS and not any(
                type(owner) is cls.FUNCTION_NODE_CLASS for owner, _ in stack
            ):
                raise self._error(node, "'return' is only valid inside a function")

            if stack:
                stack[-1][1].block.append(node)
            else:
                self.post_blockenize.append(node)

        if stack:
            owner, _ = stack[-1]
            raise self._error(
                owner, f"missing 'end' for '{cls.BLOCK_NAMES[type(owner)]}' block opened here"
            )
        return self.post_blockenize
