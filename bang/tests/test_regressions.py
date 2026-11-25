"""End-to-end regressions that assert output, errors, and scope cleanup."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from bang.lexing.lexer import Lexer
from bang.parsing.control_flow_parser import ControlFlowParser
from bang.parsing.expression_parser import ExpressionParser
from bang.runtime.evaluator import Evaluator, EvaluatorError
from bang.semantic.semantic_analysis import SemanticAnalysis, SemanticError


def compile_program(code, *, analyze=True):
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "program.bang"
        source.write_text(code, encoding="utf-8")
        lexer = Lexer(source)
        parser = ExpressionParser(lexer.tokenizer(), lexer.text)
        parser.split()
        parser.loading_into_algos()
        roots = ControlFlowParser(lexer.text, parser.post_SYA).blockenize()
        if analyze:
            SemanticAnalysis(lexer.text, roots).walk_program()
        return Evaluator(lexer.text, roots)


class RegressionTests(unittest.TestCase):
    def assert_output(self, code, expected):
        evaluator = compile_program(code)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            evaluator.eval_program()
        self.assertEqual(output.getvalue(), expected)
        self.assertEqual(len(evaluator.scope_stack), 1)
        self.assertEqual(evaluator.loop_depth, 0)
        return evaluator

    def test_false_elif_is_skipped(self):
        self.assert_output("if false; print{1}; elif false; print{2}; end; end", "")

    def test_else_runs_after_false_elif(self):
        self.assert_output(
            "if false; print{1}; elif false; print{2}; end; else; print{3}; end; end",
            "3\n",
        )

    def test_first_true_elif_is_selected(self):
        self.assert_output(
            "if false; print{0}; elif false; print{1}; end; "
            "elif true; print{2}; end; else; print{3}; end; end", "2\n",
        )

    def test_and_short_circuits(self):
        self.assert_output("print{false && (1 / 0)}", "0\n")

    def test_or_short_circuits(self):
        self.assert_output("print{true || (1 / 0)}", "1\n")

    def test_logic_preserves_operand_values(self):
        self.assert_output('x = "hello" || "world"; print{x + "!", [] || [2]}',
                           "hello! [2]\n")

    def test_compound_rhs_runs_once(self):
        self.assert_output(
            "fn tick args; print{7}; return 1; end; x = 0; x += tick{}; print{x}",
            "7\n1\n",
        )

    def test_compound_index_and_rhs_run_once_in_order(self):
        self.assert_output(
            'fn where args; print{"index"}; return 0; end; '
            'fn value args; print{"rhs"}; return 3; end; '
            'xs = [1]; xs[where{}] += value{}; print{xs}',
            "index\nrhs\n[4]\n",
        )

    def test_compound_field_base_runs_once(self):
        self.assert_output(
            'data Box [value]; b = Box{1}; '
            'fn get args; print{"target"}; return b; end; '
            'fn value args; print{"rhs"}; return 2; end; '
            'get{}.value += value{}; print{b.value}',
            "target\nrhs\n3\n",
        )

    def test_nested_compound_destructuring_rhs_runs_once(self):
        self.assert_output(
            'fn values args; print{"rhs"}; return [3,[4]]; end; '
            '[a,[b]] = [1,[2]]; [a,[b]] += values{}; print{a,b}',
            "rhs\n4 6\n",
        )

    def test_function_result_can_be_destructured(self):
        self.assert_output(
            "fn pair args; return [1,2]; end; [a,b] = pair{}; print{a,b}", "1 2\n",
        )

    def test_nested_dynamic_destructuring(self):
        self.assert_output(
            "fn pair args; return [1,[2]]; end; [a,[b]] = pair{}; print{a,b}",
            "1 2\n",
        )

    def test_unknown_array_shape_can_be_destructured(self):
        self.assert_output("[a,b] = [1] + [2]; print{a,b}", "1 2\n")

    def test_dynamic_unpack_checks_length_at_runtime(self):
        with self.assertRaises(EvaluatorError):
            compile_program("fn pair args; return [1]; end; [a,b] = pair{}").eval_program()

    def test_branch_type_changes_do_not_poison_following_code(self):
        self.assert_output('x = 1; if false; x = "s"; end; print{x + 1}', "2\n")

    def test_branches_start_from_independent_type_environments(self):
        self.assert_output(
            'x = 1; if false; x = "s"; elif false; print{x + 1}; end; '
            'else; print{x + 1}; end; end; print{x + 1}', "2\n2\n",
        )

    def test_function_definition_does_not_assign_outer_types(self):
        self.assert_output('x = 1; fn f args; x = "s"; end; print{x + 1}', "2\n")

    def test_while_local_does_not_escape(self):
        with self.assertRaises(SemanticError):
            compile_program("while false; x = 1; end; print{x}")

    def test_while_updates_existing_outer_binding(self):
        self.assert_output("x = 0; while x < 2; x += 1; end; print{x}", "2\n")

    def test_while_type_change_is_conservative(self):
        self.assert_output('x = 1; while false; x = "s"; end; print{x + 1}', "2\n")

    def test_loop_can_carry_a_record_initialized_on_an_earlier_iteration(self):
        self.assert_output(
            "data Node [value,next]; head = none; tail = none; for i 3; "
            "node = Node{i}; if head == none; [head,tail] = [node,node]; "
            "else; tail.next = node; tail = node; end; end; end; print{head.next.value}",
            "1\n",
        )

    def test_for_bound_is_checked(self):
        with self.assertRaises(SemanticError):
            compile_program("for i missing; end")

    def test_dynamic_callee_arguments_are_checked(self):
        with self.assertRaises(SemanticError):
            compile_program("fn f args; return len; end; f{}{missing}")

    def test_function_cannot_break_its_callers_loop(self):
        with self.assertRaises(SemanticError):
            compile_program("for i 1; fn f args; break; end; f{}; end")

    def test_runtime_also_rejects_cross_function_break(self):
        evaluator = compile_program("for i 1; fn f args; break; end; f{}; end", analyze=False)
        with self.assertRaises(EvaluatorError):
            evaluator.eval_program()
        self.assertEqual(evaluator.loop_depth, 0)
        self.assertEqual(len(evaluator.scope_stack), 1)

    def test_continue_unwinds_if_scope(self):
        self.assert_output(
            "i = 0; total = 0; while i < 3; i += 1; "
            "if i == 1; local = 9; continue; end; total += i; end; print{total}",
            "5\n",
        )

    def test_return_unwinds_loop_and_if_scopes(self):
        self.assert_output(
            "fn f args; for i 3; if i == 1; return i; end; end; return 9; end; print{f{}}",
            "1\n",
        )

    def test_true_division_broadcasts_in_operand_order(self):
        self.assert_output("print{[2] / [4,8], [4,8] / [2]}",
                           "[0.5, 0.25] [2.0, 4.0]\n")

    def test_floor_division_broadcasts_in_operand_order(self):
        self.assert_output("print{[9] // [2,4], [9,8] // [2]}", "[4, 2] [4, 4]\n")

    def test_broadcast_zero_numerator_is_valid(self):
        self.assert_output("print{[0] / [4,8]}", "[0.0, 0.0]\n")

    def test_broadcast_zero_denominator_is_rejected(self):
        with self.assertRaises(EvaluatorError):
            compile_program("print{[2] / [4,0]}").eval_program()

    def test_division_rejects_incompatible_shapes(self):
        with self.assertRaises(EvaluatorError):
            compile_program("print{[1,2] / [3,4,5]}").eval_program()

    def test_nested_index_has_the_selected_elements_type(self):
        self.assert_output("a = [[1,2],[3,4]]; print{a[0][1] + 1}", "3\n")

    def test_string_division_has_array_result_type(self):
        self.assert_output('x = "a b" / " "; print{x + ["c"]}', "['a', 'b', 'c']\n")


if __name__ == "__main__":
    unittest.main()
