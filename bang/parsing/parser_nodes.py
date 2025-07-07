from dataclasses import dataclass, field, replace

from bang.lexing.lexer import TokenType, Lexeme, Lexer
from typing import Any, List, Optional

# data types

# it is probably worth switching around the
# type declarations for these data classes to reduce
# ambiguity but its intutive enough and python 
# really dosent enforce it so i will ignore for now
@dataclass
class IntegerLiteralNode:
    value: Any
    meta_data: Lexeme

    def __repr__(self) -> str:
        return f"IntegerLiteral({self.value})"

@dataclass
class FloatLiteralNode:
    value: Any
    meta_data: Lexeme

    def __repr__(self) -> str:
        return f"FloatLiteral({self.value})"

@dataclass
class StringLiteralNode:
    value: Any
    # the meta_data here could change but I've opted to just store the meta_data
    # to the left quote for error checking purposes because I can't think
    # of any errors where it would be necessary to highlight the entire string
    meta_data: Lexeme

    def __repr__(self) -> str:
        return f"StringLiteral({self.value!r})"

@dataclass
class IdentifierNode:
    value: Any
    meta_data: Lexeme
    def __repr__(self) -> str:
        return f"IdentifierNode({self.value!r})"

@dataclass
class BooleanLiteralNode:
    value: Any
    meta_data: Lexeme

    def __repr__(self) -> str:
        return f"BooleanLiteral({self.value})"

@dataclass
class NoneLiteralNode:
    value: Any
    meta_data: Lexeme
    def __repr__(self):
        return f"{self.value}"


@dataclass
class ExpressionNode:

    root_expr: Any

    def __repr__(self):
        return f"root_expr: {self.root_expr}"

@dataclass
class BinOpNode:
    left: Any
    op: TokenType
    meta_data: Lexeme
    right: Any

    def __repr__(self):
        return f""" BinOpNode(\n
            left: {self.left}\n
            op: {self.op}\n
            right: {self.right}\n
        ) """

@dataclass
class UnaryOPNode:
    op: TokenType
    meta_data: Lexeme
    operand: Any
    def __repr__(self):
        return f"UnaryOp({self.op}, {self.operand})"

@dataclass
class ArrayLiteralNode:
    
    elements: List[ExpressionNode]
    meta_data: Lexeme

    def __repr__(self):
        return f"ArrayLiteral({self.elements!r})"

@dataclass
class IndexNode:
    base: Any      # the expression evaluating to an array
    index: List[ExpressionNode]      # the expression for the index
    meta_data: Lexeme

    def __repr__(self):
        return f""" IndexNode (\n
                 base: ({self.base!r},\n 
                 index: {self.index!r})\n
                 )"""

@dataclass
class AssignmentNode:

    left_hand: IdentifierNode
    op: TokenType
    meta_data: Lexeme
    right_hand:  ExpressionNode

    def __repr__(self):
        return f"""AssignmentNode(\n 
                   left_hand: {self.left_hand},\n
                   op: {self.op},\n
                   right_hand: {self.right_hand}\n
                    ) """


# collection of anything (expressions, loops, ifs)
@dataclass
class BlockNode:

    block: List[Any] = field(default_factory=list)

    def __repr__(self):
        return f"Block: {[i for i in self.block]}"

#ifs
@dataclass
class IFNode:

    condition: ExpressionNode
    meta_data: Lexeme
    body: BlockNode = field(default_factory=BlockNode)
    elif_branch: BlockNode = field(default_factory=BlockNode)
    else_branch: BlockNode = field(default_factory=BlockNode)

    def __repr__(self) -> str:
        return (f"""
            IfNode(\n"
              condition={self.condition!r},\n
              then_branch={self.body!r},\n
              elif_branch={self.elif_branch}
              else_branch={self.else_branch!r}\n
           )"""
        )
@dataclass
class ElifNode:
    condition: ExpressionNode
    meta_data: Lexeme
    body: BlockNode = field(default_factory=BlockNode)
    def __repr__(self) -> str:
        return (f"""
            ElifNode(\n
            condition={self.condition!r},\n
            then_branch={self.body!r},\n
            )"""
                
        )
#loops
@dataclass
class ForNode:

    variable: IdentifierNode
    bound: ExpressionNode
    meta_data: Lexeme
    body: BlockNode = field(default_factory=BlockNode)
    def __repr__(self) -> str:
        return (f"""
            ForNode(\n
            variable={self.variable!r},\n
            bound={self.bound!r},\n
             body={self.body!r}\n
            """
        )
@dataclass
class WhileNode:

    condition: ExpressionNode
    meta_data: Lexeme
    body: BlockNode = field(default_factory=BlockNode)
    def __repr__(self) -> str:
        return (f"""
            WhileNode(\n
            condition={self.condition!r},\n
            body={self.body!r}\n
            """
        )


        
# single token control flow constructs

@dataclass
class ElseNode:
    meta_data: Lexeme
    body: BlockNode = field(default_factory=BlockNode)
    def __repr__(self):
        return f"""ElseNode(\n
                  body= {self.body}\n
                 )
        """
    
@dataclass
class BreakNode:
    meta_data: Lexeme
    def __repr__(self):
        return "break"
    
@dataclass
class EndNode:
    meta_data: Lexeme
    def __repr__(self):
        return "end"
    
@dataclass    
class ContinueNode:
    meta_data: Lexeme
    def __repr__(self):
        return "continue"
    
@dataclass
class ReturnNode:

    meta_data: Lexeme

    expression: ExpressionNode

    def __repr__(self):
        return f"return {self.expression}"

@dataclass
class FunctionNode:
    name: IdentifierNode
    meta_data: Lexeme
    arg_list_name: IdentifierNode
    return_expr: Optional[ReturnNode] = None
    body: BlockNode = field(default_factory=BlockNode)
    def __repr__(self) -> str:
        return (f"""
            FunctionNode(\n
            name={self.name!r},\n
            arg_list={self.arg_list_name!r}\n
            body={self.body!r}\n
            return={self.return_expr!r},\n
            """
        )

@dataclass
class CallNode:
    name: IdentifierNode
    args: List[Any]
    meta_data: Lexeme
    def __repr__(self) -> str:
        return (f"""
            CallNode(\n
            name={self.name!r},\n
            arg_list={self.args!r}\n
            """
        )

