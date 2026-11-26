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
            "if false; x = 1; elif true; x = 2; else; x = 3; end; x = 4"
        )
        roots = ControlFlowParser(text, nodes).blockenize()
        self.assertEqual(len(roots), 2)
        root = roots[0]
        self.assertEqual(len(root.elif_branch.block), 1)
        self.assertEqual(len(root.else_branch.block), 1)
        for branch, expected in ((root, 1), (root.elif_branch.block[0], 2),
                                 (root.else_branch.block[0], 3)):
            self.assertEqual(len(branch.body.block), 1)
            self.assertEqual(branch.body.block[0].right_hand.root_expr.value, expected)
        self.assertEqual(roots[1].right_hand.root_expr.value, 4)

    def test_nested_blocks_stay_in_the_active_conditional_branch(self):
        text, nodes = parse(
            "if true; if false; x = 1; else; x = 2; end; x = 3; "
            "elif true; for i 1; if true; x = 4; else; x = 5; end; end; x = 6; "
            "else; fn f args; if true; return 7; else; return 8; end; end; x = 9; "
            "end; x = 10"
        )
        outer, following = ControlFlowParser(text, nodes).blockenize()
        inner, then_tail = outer.body.block
        loop, elif_tail = outer.elif_branch.block[0].body.block
        function, else_tail = outer.else_branch.block[0].body.block
        self.assertEqual(inner.else_branch.block[0].body.block[0].right_hand.root_expr.value, 2)
        self.assertEqual(len(loop.body.block[0].else_branch.block), 1)
        self.assertEqual(len(function.body.block[0].else_branch.block), 1)
        self.assertEqual([node.right_hand.root_expr.value for node in
                          (then_tail, elif_tail, else_tail, following)], [3, 6, 9, 10])

    def test_conditional_structure_errors_identify_the_offending_header(self):
        cases = (
            ("elif true; end", "no matching open 'if'"),
            ("else; end", "no matching open 'if'"),
            ("if true; else; else; end", "else must be the last branch"),
            ("if true; else; elif false; end", "else must be the last branch"),
            ("if true; for i 1; else; end; end", "close the 'for' block first"),
            ("if true; while false; elif true; end; end", "close the 'while' block first"),
            ("if true; fn f args; else; end; end", "close the 'fn' block first"),
            ("if true; else; end; end", "no matching open block"),
            ("if false; elif true; end; else; end", "no matching open 'if'"),
            ("return 1", "only valid inside a function"),
        )
        for code, message in cases:
            with self.subTest(code=code), self.assertRaisesRegex(ParserError, message):
                text, nodes = parse(code)
                ControlFlowParser(text, nodes).blockenize()

    def test_missing_end_points_to_the_innermost_block_owner(self):
        for code, kind, row in (
            ("\nif true\nelse\nx = 1", "if", 2),
            ("if false\nelif true\nx = 1", "if", 1),
            ("if true\nelse\nfor i 1", "for", 3),
            ("if true\nelse\nwhile false", "while", 3),
            ("if true\nelse\nfn f args", "fn", 3),
            ("if true\nelse\nif false", "if", 3),
        ):
            with self.subTest(code=code), self.assertRaises(ParserError) as error:
                text, nodes = parse(code)
                ControlFlowParser(text, nodes).blockenize()
            self.assertEqual(error.exception.row, row)
            self.assertEqual(error.exception.msg, f"missing 'end' for '{kind}' block opened here")

    def test_branches_share_one_block_depth_slot(self):
        depth = ControlFlowParser.MAX_BLOCK_DEPTH
        for code in (
            "if true; " * depth + "else; " + "end; " * depth,
            "if false; " + "elif false; " * 200 + "else; end",
        ):
            with self.subTest(code=code):
                text, nodes = parse(code)
                self.assertEqual(len(ControlFlowParser(text, nodes).blockenize()), 1)
        with self.assertRaisesRegex(ParserError, "block nesting exceeds"):
            text, nodes = parse("if true; " * (depth + 1) + "end; " * (depth + 1))
            ControlFlowParser(text, nodes).blockenize()

    def test_unmatched_blocks_raise_parser_error(self):
        for code in ("end", "if true; x = 1", "else; end"):
            with self.subTest(code=code), self.assertRaises(ParserError):
                text, nodes = parse(code)
                ControlFlowParser(text, nodes).blockenize()

    def test_parameter_declarations_and_keyword_argument_ast(self):
        _, nodes = parse('fn f {input, frozen=false, xs=[1,2],}; end; f{arr,frozen=true}')
        self.assertIsNone(nodes[0].arg_list_name)
        self.assertEqual([p.name for p in nodes[0].parameters], ['input', 'frozen', 'xs'])
        self.assertIsNone(nodes[0].parameters[0].default)
        self.assertEqual(nodes[2].root_expr.keyword_names, (None, 'frozen'))
        self.assertEqual(len(nodes[2].root_expr.args), 2)
        _, nodes = parse('fn f args {frozen=false}; end')
        self.assertEqual(nodes[0].arg_list_name, 'args')
        self.assertEqual([p.name for p in nodes[0].parameters], ['frozen'])

    def test_malformed_signatures_and_keyword_calls_are_rejected(self):
        for code in (
            'fn f {x,x}; end', 'fn f {x=1,y}; end', 'fn f {,x}; end',
            'fn f {x,,y}; end', 'fn f {1}; end', 'fn f {x=}; end',
            'fn f {x=1} extra; end', 'fn f {x=[1,2)}; end',
            'f{x=1,x=2}', 'f{x=1,2}', 'f{x=}', 'f{x.y=1}',
            'f{x=(y=1)}', 'f{x=[y=1]}', 'a = x = 1',
            'fn f args {args=1}; end', 'fn f args extra; end',
        ):
            with self.subTest(code=code), self.assertRaises(ParserError):
                parse(code)


if __name__ == "__main__":
    unittest.main()
