# after this pass we are guaranteed to have a completely
# syntactically valid bang program.
# all constructs were able to be formed and now we have
# a proper nested structuring of the program,
# with essentially a control-flow-graph on the macro
# "block" level, and nested ASTS on the micro
# "line" level

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
        ELIF_NODE_CLASS,
        FOR_NODE_CLASS,
        WHILE_NODE_CLASS,
        ELSE_NODE_CLASS,
        FUNCTION_NODE_CLASS,
    )

    DEPENDANT_NODES = (ELIF_NODE_CLASS, ELSE_NODE_CLASS)

    def __init__(self, file, expression_nodes):
        self.file = file

        self.expression_nodes = expression_nodes

        # so you can imagine all of the expression level lines will either live
        # with a control flow construct or not. if it dosen't, then it will appear in
        # post_blockenize as a bare expression node (global node), if it does, it will be apart
        # of one of the control flow contructs' blocks

        self.post_blockenize = []

    def blockenize(self):
        cls = self.__class__
        DEPENDANT_NODES = cls.DEPENDANT_NODES
        CONTROL_FLOW_NODES = cls.CONTROL_FLOW_NODES
        ELIF_NODE_CLASS = cls.END_NODE_CLASS
        END_NODE_CLASS = cls.END_NODE_CLASS
        FUNCTION_NODE_CLASS = cls.FUNCTION_NODE_CLASS
        IF_NODE_CLASS = cls.IF_NODE_CLASS
        # stack is going to be our current control-flow construct we are in
        # once we see an end, we pop of the stack and either add it to the post blockenize
        # or add it to the thing behind it in the stack (meaning it's a nested construct)
        stack = []

        for node in self.expression_nodes:
            # so if we see a control flow construct,
            # we just add it to the stack and if we
            # see a non construct, add it to the body
            # its nested in
            type_node = type(node)
            if type_node in CONTROL_FLOW_NODES:
                stack.append(node)
            elif type_node is END_NODE_CLASS:
                if not stack:
                    raise ParserError(
                        self.file,
                        "end statement missing matching construct (no construct exists)",
                        node.meta_data.line,
                        node.meta_data.column_start,
                        node.meta_data.column_end,
                    )
                construct = stack.pop()
                type_construct = type(construct)
                if type_construct in DEPENDANT_NODES:
                    if not stack or (type(stack[-1]) is not IF_NODE_CLASS):
                        raise ParserError(
                            self.file,
                            "This construct is dependant on an if statement",
                            construct.meta_data.line,
                            construct.meta_data.column_start,
                            construct.meta_data.column_end,
                        )
                    if type_construct is ELIF_NODE_CLASS:
                        stack[-1].elif_branch.block.append(construct)
                    else:
                        stack[-1].else_branch.block.append(construct)
                else:
                    if not stack:
                        self.post_blockenize.append(construct)
                    else:
                        stack[-1].body.block.append(construct)
            elif type_node is RETURN_NODE_CLASS:
                if not any(type(item) is FUNCTION_NODE_CLASS for item in stack):
                    raise ParserError(
                        self.file,
                        "missing matching construct",
                        node.meta_data.line,
                        node.meta_data.column_start,
                        node.meta_data.column_end,
                    )
                if not stack:
                    self.post_blockenize.append(node)
                else:
                    stack[-1].body.block.append(node)
            else:
                if not stack:
                    self.post_blockenize.append(node)
                else:
                    stack[-1].body.block.append(node)
        if stack:
            missing_end_node = stack.pop()
            raise ParserError(
                self.file,
                "missing matching construct",
                missing_end_node.meta_data.line,
                missing_end_node.meta_data.column_start,
                missing_end_node.meta_data.column_end,
            )
        return self.post_blockenize
