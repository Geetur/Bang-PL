"""Parser behavior tests; runnable with pytest or the standard unittest runner."""

import tempfile
import unittest
from pathlib import Path

from bang.lexing.lexer import Lexer
from bang.lexing.lexer_tokens import TokenType
from bang.parsing.control_flow_parser import ControlFlowParser
from bang.parsing.expression_parser import ExpressionParser, ParserError
from bang.parsing.parser_nodes import BinOpNode, CallNode, FieldAccessNode, IndexNode, UnaryOPNode


def parse(code):
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "program.bang"
        source.write_text(code, encoding="utf-8")
        lexer = Lexer(source)
        parser = ExpressionParser(lexer.tokenizer(), lexer.text)
        parser.split()
        parser.loading_into_algos()
        return lexer.text, parser.post_SYA


class ParserCorrectnessTests(unittest.TestCase):
    def test_multiplication_binds_more_tightly_than_addition(self):
        _, nodes = parse("1 + 2 * 3")
        root = nodes[0].root_expr
        self.assertIsInstance(root, BinOpNode)
        self.assertEqual(root.op, TokenType.T_PLUS)
        self.assertEqual(root.right.op, TokenType.T_ASTERISK)

    def test_exponentiation_is_right_associative(self):
        _, nodes = parse("2 ** 3 ** 2")
        root = nodes[0].root_expr
        self.assertEqual(root.op, TokenType.T_EXPO)
        self.assertEqual(root.left.value, 2)
        self.assertEqual(root.right.op, TokenType.T_EXPO)

    def test_subtraction_is_left_associative(self):
        _, nodes = parse("9 - 3 - 1")
        root = nodes[0].root_expr
        self.assertEqual(root.op, TokenType.T_MINUS)
        self.assertEqual(root.left.op, TokenType.T_MINUS)
        self.assertEqual(root.right.value, 1)

    def test_unary_wraps_an_indexed_operand(self):
        _, nodes = parse("-a[0]")
        self.assertIsInstance(nodes[0].root_expr, UnaryOPNode)
        self.assertIsInstance(nodes[0].root_expr.operand, IndexNode)

    def test_call_index_field_chaining(self):
        _, nodes = parse("f{}[0].x")
        root = nodes[0].root_expr
        self.assertIsInstance(root, FieldAccessNode)
        self.assertIsInstance(root.base, IndexNode)
        self.assertIsInstance(root.base.base, CallNode)

    def test_nested_calls_and_arrays(self):
        _, nodes = parse("print{sum{[1,2]}, [3,[4]]}")
        root = nodes[0].root_expr
        self.assertEqual(len(root.args), 2)
        self.assertIsInstance(root.args[0].root_expr, CallNode)
        self.assertEqual(len(root.args[1].root_expr.elements), 2)

    def test_empty_collections_and_trailing_commas(self):
        _, nodes = parse("a = []; b = [1,2,]; f{}")
        self.assertEqual(len(nodes), 3)
        self.assertEqual(len(nodes[0].right_hand.root_expr.elements), 0)
        self.assertEqual(len(nodes[1].right_hand.root_expr.elements), 2)

    def test_malformed_expressions_raise_parser_error(self):
        for code in (
            "print{1]", "x = [1}", "f{[1}}", "f{1+}", "x = 1 +",
            "x =", "= 1", "a[]", "()", "1(2)", "*1", "1 + *2",
            "a[1+2}", "1 + )", "(", "!", "a.", "f{1",
        ):
            with self.subTest(code=code), self.assertRaises(ParserError):
                parse(code)

    def test_elif_and_else_have_separate_ast_branches(self):
        text, nodes = parse(
            "if false; print{1}; elif true; print{2}; end; "
            "else; print{3}; end; end"
        )
        root = ControlFlowParser(text, nodes).blockenize()[0]
        self.assertEqual(len(root.elif_branch.block), 1)
        self.assertEqual(len(root.else_branch.block), 1)

    def test_unmatched_blocks_raise_parser_error(self):
        for code in ("end", "if true; x = 1", "else; end"):
            with self.subTest(code=code), self.assertRaises(ParserError):
                text, nodes = parse(code)
                ControlFlowParser(text, nodes).blockenize()


if __name__ == "__main__":
    unittest.main()
