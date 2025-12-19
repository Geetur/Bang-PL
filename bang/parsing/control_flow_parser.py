# after this pass we are guaranteed to have a completely
# syntactically valid bang program.
# all constructs were able to be formed and now we have
# a proper nested structuring of the program,
# with essentially a control-flow-graph on the macro
# "block" level, and nested ASTS on the micro
# "line" level

from bang.parsing.expression_parser import ParserError
from bang.parsing.parser_nodes import (
    ElifNode,
    ElseNode,
    EndNode,
    ForNode,
    FunctionNode,
    IFNode,
    ReturnNode,
    WhileNode,
)


class ControlFlowParser:
    def __init__(self, file, expression_nodes):
        self.file = file

        self.expression_nodes = expression_nodes

        # so you can imagine all of the expression level lines will either live
        # with a control flow construct or not. if it dosen't, then it will appear in
        # post_blockenize as a bare expression node (global node), if it does, it will be apart
        # of one of the control flow contructs' blocks

        self.post_blockenize = []

    def blockenize(self):
        # stack is going to be our current control-flow construct we are in
        # once we see an end, we pop of the stack and either add it to the post blockenize
        # or add it to the thing behind it in the stack (meaning it's a nested construct)
        stack = []

        control_flow_nodes = {
            IFNode,
            ElifNode,
            ForNode,
            WhileNode,
            ElseNode,
            FunctionNode,
        }

        dependant_nodes = (ElifNode, ElseNode)

        for node in self.expression_nodes:
            # so if we see a control flow construct,
            # we just add it to the stack and if we
            # see a non construct, add it to the body
            # its nested in
            if type(node) in control_flow_nodes:
                stack.append(node)
            elif type(node) is EndNode:
                if not stack:
                    raise ParserError(
                        self.file,
                        "end statement missing matching construct (no construct exists)",
                        node.meta_data.line,
                        node.meta_data.column_start,
                        node.meta_data.column_end,
                    )
                construct = stack.pop()
                if type(construct) in dependant_nodes:
                    if not stack or (type(stack[-1]) is not IFNode):
                        raise ParserError(
                            self.file,
                            "This construct is dependant on an if statement",
                            construct.meta_data.line,
                            construct.meta_data.column_start,
                            construct.meta_data.column_end,
                        )
                    if type(construct) is ElifNode:
                        stack[-1].elif_branch.block.append(construct)
                    else:
                        stack[-1].else_branch.block.append(construct)
                else:
                    if not stack:
                        self.post_blockenize.append(construct)
                    else:
                        stack[-1].body.block.append(construct)
            elif type(node) is ReturnNode:
                if not any(type(item) is FunctionNode for item in stack):
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
