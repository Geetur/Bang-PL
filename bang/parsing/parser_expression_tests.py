import pytest
from pathlib import Path

from bang.lexing.lexer import Lexer
from bang.parsing.expression_parser import ExpressionParser, ParserError
from bang.parsing.parser_nodes import (
    IntegerLiteralNode, FloatLiteralNode, BooleanLiteralNode,
    IdentifierNode, BinOpNode, UnaryOPNode, ArrayLiteralNode,
    StringLiteralNode, IndexNode, AssignmentNode,
    IFNode, ForNode, WhileNode, ElseNode,
    BreakNode, ContinueNode, ReturnNode, ExpressionNode, EndNode
)
from typing import List

def parse_lines(code, tmp_path):
    # write code to temporary file
    file = tmp_path / "code.txt"
    file.write_text(code)
    # lex
    lexer = Lexer(str(file))
    tokens = lexer.tokenizer()
    # parse
    lines = code.splitlines(keepends=True)
    parser = ExpressionParser(tokens, lines)
    parser.split()
    nodes = parser.loading_into_algos()
    return nodes


def test_assignment_and_return(tmp_path):
    code = """
    x = 1 + 2
    return x
    """
    nodes = parse_lines(code, tmp_path)
    # Expect two nodes: AssignmentNode and ReturnNode
    assert len(nodes) == 2
    assign, ret = nodes
    assert isinstance(assign, AssignmentNode)
    # Check identifier on left-hand side
    assert assign.left_hand.value == "x"
    # Check expression inside assignment
    expr_node = assign.right_hand
    assert isinstance(expr_node, ExpressionNode)
    # The root inside ExpressionNode is a BinOpNode
    assert isinstance(expr_node.root_expr, BinOpNode)
    # Check return node
    assert isinstance(ret, ReturnNode)


def test_unary_and_binary_operations(tmp_path):
    code = "value = -3 * (4 + +5)"
    nodes = parse_lines(code + "\n", tmp_path)
    assert len(nodes) == 1
    assign = nodes[0]
    assert isinstance(assign, AssignmentNode)
    # Get the top-level BinOpNode
    expr_node = assign.right_hand
    binop = expr_node.root_expr
    assert isinstance(binop, BinOpNode)
    left, op, right = binop.left, binop.op, binop.right
    # Left should be a UnaryOPNode
    assert isinstance(left, UnaryOPNode)
    # Operator should be multiplication
    from bang.lexing.lexer import TokenType as TT
    assert op == TT.T_ASTERISK
    # Right should be an ExpressionNode nested
    assert isinstance(right, BinOpNode)


def test_array_and_index(tmp_path):
    code = "arr = [1, 2, 3]\nnext = arr[1]"
    nodes = parse_lines(code, tmp_path)
    assert len(nodes) == 2
    arr_assign, next_assign = nodes
    # Test array literal
    assert isinstance(arr_assign, AssignmentNode)
    array_expr = arr_assign.right_hand.root_expr
    assert isinstance(array_expr, ArrayLiteralNode)
    assert len(array_expr.elements) == 3
    # Test index node
    assert isinstance(next_assign, AssignmentNode)
    idx_expr = next_assign.right_hand.root_expr
    assert isinstance(idx_expr, IndexNode)
    assert isinstance(idx_expr.index[0], ExpressionNode)


def test_string_literal(tmp_path):
    code = 'msg = "hello"\n'
    nodes = parse_lines(code, tmp_path)
    assert len(nodes) == 1
    assign = nodes[0]
    assert isinstance(assign, AssignmentNode)
    str_expr = assign.right_hand.root_expr
    assert isinstance(str_expr, StringLiteralNode)
    assert str_expr.value == "hello"


def test_control_structures(tmp_path):
    code = """
    if x < 10
    else
    for i 5
    while true
    break
    continue
    end
    return 0
    """
    nodes = parse_lines(code, tmp_path)
    # Expect nodes in sequence
    types = [IFNode, ElseNode, ForNode, WhileNode, BreakNode, ContinueNode, EndNode, ReturnNode]
    assert len(nodes) == len(types)
    for node, expected in zip(nodes, types):
        assert isinstance(node, expected)


def test_parser_error_mismatched_parenthesis(tmp_path):
    code = "x = (1 + 2\n"
    with pytest.raises(ParserError):
        parse_lines(code, tmp_path)


def test_parser_error_invalid_assignment(tmp_path):
    code = "= 5 + 3\n"
    with pytest.raises(ParserError):
        parse_lines(code, tmp_path)

def test_float_operations(tmp_path):
    code = "result = 3.5 * 2.0 + 1.25"
    nodes = parse_lines(code + "\n", tmp_path)
    assert len(nodes) == 1
    assign = nodes[0]
    assert isinstance(assign, AssignmentNode)
    expr = assign.right_hand.root_expr
    assert isinstance(expr, BinOpNode)
    # Ensure left side float literal
    left = expr.left
    assert isinstance(left, BinOpNode)
    # Right side is nested BinOpNode
    assert isinstance(expr.right, FloatLiteralNode)

def test_boolean_literal(tmp_path):
    code = "flag = true && false || true"
    nodes = parse_lines(code + "\n", tmp_path)
    assert len(nodes) == 1
    assign = nodes[0]
    expr = assign.right_hand.root_expr
    # Top-level OR
    assert isinstance(expr, BinOpNode)
    # Check boolean literal types
    left_and = expr.left
    assert isinstance(left_and, BinOpNode)
    assert isinstance(left_and.left, BooleanLiteralNode)
    assert isinstance(left_and.right, BooleanLiteralNode)
    # Right operand of OR
    assert isinstance(expr.right, BooleanLiteralNode)

def test_exponent_precedence(tmp_path):
    code = "val = 2 ** 3 ** 2"
    nodes = parse_lines(code + "\n", tmp_path)
    assign = nodes[0]
    expr = assign.right_hand.root_expr
    # Exponent is right-associative: 3 ** 2 evaluated first
    assert isinstance(expr, BinOpNode)
    assert expr.op.name == 'T_EXPO'
    # Right operand of outer ** is a BinOpNode
    assert isinstance(expr.right, BinOpNode)

# its really important to remember here that an array isn't an expression
# in our langauge, its a container of expressions. this might be somewhat confusing
# because if you pass an array into the SYA it will be wrapped in a expression node, but that is only
# because its the root expression. all an expression node is in this lanaguge
def test_array_nesting(tmp_path):
    code = "arr = [[1,2], [3, [4,5]]]"
    nodes = parse_lines(code + "\n", tmp_path)
    assign = nodes[0]
    array_node = assign.right_hand.root_expr
    assert isinstance(array_node, ArrayLiteralNode)
    # Two top-level elements
    assert len(array_node.elements) == 2
    # First element is an ArrayLiteralNode wrapped in ExpressionNode

    first = array_node.elements[0]
    
    assert isinstance(first, ArrayLiteralNode)
    # Nested deeper
    second = array_node.elements[1]
    assert isinstance(second, ArrayLiteralNode)
    inner = second.elements[1]
    assert isinstance(inner, ArrayLiteralNode)

def test_invalid_indexing_error(tmp_path):
    code = "5[0]"
    with pytest.raises(ParserError):
        parse_lines(code + "\n", tmp_path)

def test_compound_assignment(tmp_path):
    code = "count = 1\ncount += 2"
    nodes = parse_lines(code + "\n", tmp_path)
    assert len(nodes) == 2
    _, plus_assign = nodes
    assert isinstance(plus_assign, AssignmentNode)
    assert plus_assign.op.name == 'T_PLUS_ASSIGN'

def test_parser_error_mismatched_brackets(tmp_path):
    code = "arr = [1, 2, 3"  # missing closing bracket
    with pytest.raises(ParserError):
        parse_lines(code + "\n", tmp_path)

def test_nested_parentheses(tmp_path):
    code = "x = ((1 + 2) * 3) - 4"
    nodes = parse_lines(code + "\n", tmp_path)
    assert len(nodes) == 1
    assign = nodes[0]
    # should parse without error and produce an AssignmentNode
    from bang.parsing.parser_nodes import AssignmentNode, BinOpNode
    assert isinstance(assign, AssignmentNode)
    # check that inside the ExpressionNode there's a BinOpNode
    expr = assign.right_hand
    assert hasattr(expr, "root_expr")
    assert isinstance(expr.root_expr, BinOpNode)

def test_empty_parentheses_error(tmp_path):
    with pytest.raises(ParserError):
        parse_lines("x = ()\n", tmp_path)


# 2. Unary-operator edge-cases

def test_multiple_unary_operators(tmp_path):
    code = "x = + - + - 5"
    nodes = parse_lines(code + "\n", tmp_path)
    assert len(nodes) == 1
    from bang.parsing.parser_nodes import AssignmentNode
    assert isinstance(nodes[0], AssignmentNode)

def test_unary_missing_operand_error(tmp_path):
    with pytest.raises(ParserError):
        parse_lines("x = +\n", tmp_path)
    with pytest.raises(ParserError):
        parse_lines("x = -\n", tmp_path)


def test_chained_indexing(tmp_path):
    code = "val = arr[1][2][i + 1]"
    nodes = parse_lines(code + "\n", tmp_path)
    assert len(nodes) == 1
    from bang.parsing.parser_nodes import AssignmentNode
    assert isinstance(nodes[0], AssignmentNode)


# 4. Logical vs. relational mixing

def test_logical_and_relational(tmp_path):
    code = "flag = a < b && c > d || !e"
    nodes = parse_lines(code + "\n", tmp_path)
    assert len(nodes) == 1


# 5. Literal edge-cases

def test_float_without_leading_zero(tmp_path):
    code = "x = .5 * 2"
    nodes = parse_lines(code + "\n", tmp_path)
    assert len(nodes) == 1
    from bang.parsing.parser_nodes import AssignmentNode
    assert isinstance(nodes[0], AssignmentNode)



def test_consecutive_operators_error(tmp_path):
    with pytest.raises(ParserError):
        parse_lines("x = 1 +* 2\n", tmp_path)

def test_array_missing_comma_error(tmp_path):
    with pytest.raises(ParserError):
        parse_lines("x = [1 2, 3]\n", tmp_path)

def test_mismatched_index_brackets_error(tmp_path):
    with pytest.raises(ParserError):
        parse_lines("x = arr[1,2]\n", tmp_path)

def test_indexing_after_expression(tmp_path):
    with pytest.raises(ParserError):
        parse_lines("val = (a + b)[2]\n", tmp_path)

