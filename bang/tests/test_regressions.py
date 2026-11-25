"""End-to-end regressions that assert output, errors, and scope cleanup."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from bang.cli import run_file
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

    def test_indirect_mutations_invalidate_shared_type_facts(self):
        cases = [
            'a=[1]; d=dict{"x",a}; d["x"][0]="hi"; print{a[0]+"!"}',
            'data P [x]; p=P{1}; d=dict{"p",p}; d["p"].x="hi"; print{p.x+"!"}',
            'a=[1]; b=min{[a]}; b[0]="hi"; print{a[0]+"!"}',
            'a=[1]; b=sort{[a]}[0]; b[0]="hi"; print{a[0]+"!"}',
            'data P [x]; p=P{1}; b=([p]+[])[0]; b.x="hi"; print{p.x+"!"}',
            'data P [x]; p=P{1}; for item [p]; item.x="hi"; print{p.x+"!"}; end',
            'a=[1]; b=max{[a]}; [b[0]]=["hi"]; print{a[0]+"!"}',
            'a=["h"]; d=dict{"x",a}; d["x"][0]+="i"; print{a[0]+"!"}',
        ]
        for code in cases:
            with self.subTest(code=code):
                self.assert_output(code, "hi!\n")

    def test_control_flow_preserves_or_widens_record_aliases(self):
        for control in ('if true; end', 'for i 0; end', 'while false; end'):
            code = 'data P [x]; p=P{0}; q=p; '+control+'; p.x="s"; q.x=1; print{p.x+1}'
            with self.subTest(control=control):
                self.assert_output(code, "2\n")
                # Proven sharing should still diagnose a known invalid operation.
                with self.assertRaises(SemanticError):
                    compile_program(code.replace('p.x+1', 'p.x+"!"'))
        for condition, expression, expected in (
            ('true', 'p.x+1', '2\n'), ('false', 'p.x+"!"', 's!\n'),
        ):
            with self.subTest(condition=condition):
                self.assert_output(
                    'data P [x]; p=P{0}; q=P{0}; if '+condition+'; q=p; end; '
                    'p.x="s"; q.x=1; print{'+expression+'}', expected,
                )

    def test_dictionary_iteration_mutation_is_controlled(self):
        for body in ('d["b"]=2', 'grow{}', 'd["b"]=2; continue'):
            code = 'd=dict{"a",1}; fn grow args; d["b"]=2; end; for k d; '+body+'; end'
            with self.subTest(body=body):
                evaluator = compile_program(code)
                with self.assertRaisesRegex(EvaluatorError, 'changed during iteration'):
                    evaluator.eval_program()
                self.assertEqual(len(evaluator.scope_stack), 1)
                self.assertEqual(evaluator.loop_depth, 0)
                self.assertEqual(evaluator.func_depth, 0)
        for code, expected in (
            ('d=dict{"a",1}; for k d; d[k]+=1; end; print{d["a"]}', '2\n'),
            ('d=dict{"a",1}; for k d; d["b"]=2; break; end; print{len{d}}', '2\n'),
            ('for k dict{}; print{k}; end', ''),
        ):
            with self.subTest(code=code):
                self.assert_output(code, expected)
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'iteration.bang'
            source.write_text('d=dict{"a",1}\nfor k d\nd["b"]=2\nend\n', encoding='utf-8')
            error = io.StringIO()
            with contextlib.redirect_stderr(error):
                self.assertEqual(run_file(str(source)), 4)
            self.assertIn('[EvaluatorError] Line 2,', error.getvalue())
            self.assertNotIn('Traceback', error.getvalue())

    def test_numeric_results_remain_finite_across_arrays_and_builtins(self):
        expressions = [
            'big*2', '[big]*[2]', '[big]*[2,3]', '[2,3]*[big]',
            '[big]/[tiny]', '[big]/[tiny,tiny]', '[big,big]/[tiny]',
            '[big]//[tiny]', 'sum{big,big}', 'sum{[big,big]}', 'sum{set{big,big*0.9}}',
            '(-1)**0.5',
        ]
        for expression in expressions:
            with self.subTest(expression=expression):
                evaluator = compile_program('big=10.0**308; tiny=10.0**-308; '+expression)
                with self.assertRaises(EvaluatorError):
                    evaluator.eval_program()
        self.assert_output(
            'big=10.0**308; print{[big]*[1],sum{big,-big},sum{[]},[0]/[2],[]*[big]}',
            '[1e+308] 0.0 0 [0.0] []\n',
        )


if __name__ == "__main__":
    unittest.main()
