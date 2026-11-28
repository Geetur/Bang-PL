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
        self.assert_output('if false; print{1}; elif false; print{2}; end', "")

    def test_else_runs_after_false_elif(self):
        self.assert_output(
            'if false; print{1}; elif false; print{2}; else; print{3}; end',
            "3\n",
        )

    def test_first_true_elif_is_selected(self):
        self.assert_output(
            'if false; print{0}; elif false; print{1}; '
            'elif true; print{2}; else; print{3}; end', "2\n",
        )

    def test_single_end_nested_branches_and_control_transfers(self):
        cases = (
            ("if true; if false; print{1}; else; print{2}; end; print{3}; "
             "else; print{0}; end; print{4}", "2\n3\n4\n"),
            ("if false; if true; print{0}; end; elif true; for i 2; "
             "if i == 0; print{10}; else; print{11}; end; end; print{12}; "
             "else; print{0}; end; print{13}", "10\n11\n12\n13\n"),
            ("total = 0; for i 5; if i == 0; continue; elif i == 3; break; "
             "else; total += i; end; total += 10; end; print{total}", "23\n"),
            ("i = 0; total = 0; while i < 5; i += 1; if i == 1; continue; "
             "elif i == 4; break; else; total += i; end; end; print{total}", "5\n"),
            ("fn f {x}; for i 1; if x == 0; return 10; elif x == 1; return 20; "
             "else; return 30; end; end; return 99; end; print{f{0},f{1},f{2}}",
             "10 20 30\n"),
            ("if true; elif false; else; end; if false; elif true; else; end; "
             "if false; else; end; print{1}", "1\n"),
            ("if false\n print{0}\nelif true\n # selected branch\n print{1}\n"
             "else\n print{0}\nend\nprint{2}", "1\n2\n"),
        )
        for code, expected in cases:
            with self.subTest(code=code):
                evaluator = self.assert_output(code, expected)
                self.assertEqual(evaluator.func_depth, 0)

    def test_single_end_conditions_are_lazy_and_branch_locals_do_not_escape(self):
        self.assert_output(
            'fn probe {value}; print{value}; return value; end; '
            'if probe{0}; print{"wrong"}; elif probe{1}; print{"selected"}; '
            'elif probe{2}; print{"wrong"}; else; print{"wrong"}; end; print{"after"}',
            '0\n1\nselected\nafter\n',
        )
        self.assert_output(
            'if true; print{"selected"}; elif 1 / 0; print{"wrong"}; end',
            'selected\n',
        )
        for code in (
            "if true; local = 1; else; local = 2; end; print{local}",
            "if false; local = 1; elif true; print{local}; end",
            "if false; local = 1; else; print{local}; end",
        ):
            with self.subTest(code=code), self.assertRaises(SemanticError):
                compile_program(code)

    def test_single_end_cli_reports_structure_errors_without_a_traceback(self):
        cases = (
            ("for i 1\nif true\nelse\n", 2, "missing 'end' for 'if'"),
            ("if true\nelse\nend\nend", 4, "no matching open block"),
            ("if false\nelse\nelif true\nend", 3, "else must be the last branch"),
        )
        for code, row, message in cases:
            with self.subTest(code=code), tempfile.TemporaryDirectory() as directory:
                source = Path(directory) / "program.bang"
                source.write_text(code, encoding="utf-8")
                diagnostic = io.StringIO()
                with contextlib.redirect_stderr(diagnostic):
                    self.assertEqual(run_file(str(source)), 2)
                self.assertIn(f"Line {row},", diagnostic.getvalue())
                self.assertIn(message, diagnostic.getvalue())
                self.assertNotIn("Traceback", diagnostic.getvalue())

    def test_and_short_circuits(self):
        self.assert_output("print{false && (1 / 0)}", "0\n")

    def test_multiline_expressions_work_across_language_constructs(self):
        cases = (
            (
                'fn transform {\n input,\n frozen=false,\n}\n return [input,frozen]\nend\n'
                'values = [1,2]\nresult = transform{\n input = values,\n frozen = true,\n}\n'
                'grid = [\n [1,2,3],\n [4,5,6],\n]\nprint{result,grid}',
                '[[1, 2], 1] [[1, 2, 3], [4, 5, 6]]\n',
            ),
            (
                'fn total args {\n bias = sum{\n args,\n},\n}\n'
                'return sum{args} + bias\nend\n'
                'print{\n total{\n 1,\n 2,\n bias=(\n 4 +\n 1\n),\n},\n total{1,2},\n}',
                '8 6\n',
            ),
            (
                'data Box [\n value,\n next\n]\nbox = Box{\n [\n 1,\n 2,\n],\n}\n'
                'box.value[\n 0\n] += (\n 4 +\n 5\n)\n'
                '[\n a,\n b\n] = box.value\nprint{a,b}',
                '10 2\n',
            ),
            (
                'x = 0\nwhile (\n x <\n 2\n)\n x += 1\nend\n'
                'for value [\n 1,\n 2,\n]\n'
                'if (\n value == 1\n)\n print{\n value + x,\n}\n'
                'elif (\n value == 2\n)\n print{value+x}\nend\nend\n'
                'if (\n false && (1/0)\n)\n print{0}\nend',
                '3\n4\n',
            ),
            (
                'fn make args; return [[[len]]]; end\nprint{\n'
                'make{\n}[\n0\n][\n0\n][\n0\n]{\n"ab",\n},\n}',
                '2\n',
            ),
            (
                'fn mark {label,value}; print{label}; return value; end\n'
                'fn pair {\n a,\n b=mark{\n "default",\n 9,\n},\n}\n'
                'return [a,b]\nend\n'
                'print{\n pair{\n mark{\n "first",\n 1,\n},\n'
                'b=mark{\n "second",\n 2,\n},\n},\n}',
                'first\nsecond\n[1, 2]\n',
            ),
            (
                'print{\n [],\n dict{\n},\n set{\n},\n "# []{}();",\n}\n'
                'x = 1\n+2\nprint{x}; print{\n 3\n}; print{4}',
                '[] {} set() # []{}();\n1\n3\n4\n',
            ),
        )
        for code, expected in cases:
            with self.subTest(code=code):
                evaluator = self.assert_output(code, expected)
                self.assertEqual(evaluator.func_depth, 0)

    def test_multiline_cli_errors_keep_physical_line_numbers(self):
        for code, status, row in (
            ('print{\n [1,2}\n}', 2, 2),
            ('print{\n 1\n', 2, 1),
            ('x = [\n missing,\n]\n', 3, 2),
            ('fn zero args; return 0; end\nprint{\n 1 / zero{\n }\n}', 4, 3),
        ):
            with self.subTest(code=code), tempfile.TemporaryDirectory() as directory:
                source = Path(directory) / 'program.bang'
                source.write_text(code, encoding='utf-8')
                diagnostic = io.StringIO()
                with contextlib.redirect_stderr(diagnostic):
                    self.assertEqual(run_file(str(source)), status)
                self.assertIn(f'Line {row},', diagnostic.getvalue())
                self.assertIn(code.splitlines()[row - 1].strip(), diagnostic.getvalue())
                self.assertNotIn('Traceback', diagnostic.getvalue())

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
            'x = 1; if false; x = "s"; elif false; print{x + 1}; '
            'else; print{x + 1}; end; print{x + 1}', "2\n2\n",
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
            'else; tail.next = node; tail = node; end; end; print{head.next.value}',
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

    def test_variadic_and_declared_function_interfaces_coexist(self):
        self.assert_output(
            'fn legacy args; return args; end; '
            'fn f {input,frozen=false}; return [input,frozen]; end; '
            'fn empty {}; return 7; end; '
            'print{legacy{},legacy{1,2},f{[1,2]},f{3,true},'
            'f{4,frozen=true},f{frozen=true,input=5},empty{}}',
            '[] [1, 2] [[1, 2], 0] [3, 1] [4, 1] [5, 1] 7\n',
        )
        self.assert_output(
            'fn f args {frozen=false}; return [args,frozen]; end; '
            'print{f{1,2},f{1,2,frozen=true},f{1,2,true},f{},f{frozen=true}}',
            '[[1, 2], 0] [[1, 2], 1] [[1, 2, 1], 0] [[], 0] [[], 1]\n',
        )

    def test_declared_parameters_work_through_first_class_function_values(self):
        for callee in ('f', 'alias', '[f][0]', 'box.callback', 'get{}'):
            with self.subTest(callee=callee):
                self.assert_output(
                    'fn f {x,y=2}; return x+y; end; alias=f; '
                    'data Box [callback]; box=Box{f}; fn get args; return f; end; '
                    'print{'+callee+'{y=4,x=3}}', '7\n',
                )
                self.assert_output(
                    'fn f args {offset=2}; return sum{args}+offset; end; alias=f; '
                    'data Box [callback]; box=Box{f}; fn get args; return f; end; '
                    'print{'+callee+'{1,2,offset=4}}', '7\n',
                )
        self.assert_output(
            'fn make {start=0}; fn next {step=1}; start+=step; return start; end; '
            'return next; end; a=make{}; b=make{start=10}; '
            'print{a{},a{step=2},b{},b{2}}', '1 3 11 13\n',
        )

    def test_defaults_are_fresh_lazy_and_use_lexical_parameter_scope(self):
        cases = [
            ('fn f {a=[0]}; a[0]+=1; return a; end; print{f{},f{}}', '[1] [1]\n'),
            ('x=1; fn f {a=x}; return a; end; x=2; print{f{}}', '2\n'),
            ('fn f {a,b=a+1,c=b+1}; return [a,b,c]; end; print{f{4},f{4,c=9}}',
             '[4, 5, 6] [4, 5, 9]\n'),
            ('x=8; fn f {x=2}; x+=1; return x; end; print{f{},x}', '3 8\n'),
            ('n=0; fn tick args; n+=1; return n; end; fn f {x=tick{}}; return x; end; '
             'print{f{0},f{false},f{none},n,f{},n}', '0 0 0 0 1 1\n'),
            ('fn f items {count=len{items},state=[0]}; state[0]+=1; '
             'return [items,count,state[0]]; end; print{f{1,2},f{3,count=0}}',
             '[[1, 2], 2, 1] [[3], 0, 1]\n'),
            ('args=[99]; frozen=8; fn f args {frozen=false}; args[0]+=1; '
             'frozen=2; return [args,frozen]; end; print{f{1},args,frozen}',
             '[[2], 2] [99] 8\n'),
        ]
        for code, expected in cases:
            with self.subTest(code=code):
                self.assert_output(code, expected)

    def test_keyword_values_and_defaults_preserve_evaluation_order(self):
        self.assert_output(
            'fn mark args; print{args[0]}; return args[1]; end; '
            'fn f {a=mark{"default-a",1},b=mark{"default-b",2},c=mark{"default-c",3}}; '
            'return [a,b,c]; end; print{f{c=mark{"c",30},b=mark{"b",20}}}',
            'c\nb\ndefault-a\n[1, 20, 30]\n',
        )
        self.assert_output(
            'fn original {x}; return x+1; end; fn other {x}; return x+10; end; '
            'f=original; fn change args; f=other; return 1; end; print{f{x=change{}}}',
            '2\n',
        )
        self.assert_output(
            'x=7; fn f {x}; return x; end; print{f{x=9},x}', '9 7\n',
        )
        self.assert_output(
            'fn mark args; print{args[0]}; return args[1]; end; '
            'fn f args {a=mark{"default",len{args}},b=0}; return [args,a,b]; end; '
            'print{f{mark{"first",1},mark{"second",2},b=mark{"option",3}}}',
            'first\nsecond\noption\ndefault\n[[1, 2], 2, 3]\n',
        )

    def test_invalid_argument_bindings_have_static_and_runtime_checks(self):
        cases = [
            'fn f {x}; return x; end; f{}',
            'fn f {}; end; f{1}',
            'fn f {x}; end; f{other=1}',
            'fn f {x}; end; f{1,x=2}',
            'fn f args; end; f{x=1}',
            'len{x=[1]}',
            'data P [x]; P{x=1}',
            'fn f args {frozen=false}; end; f{1,2,other=true}',
            'fn f args {frozen}; end; f{1,2,true}',
            'fn f args {frozen=false}; end; f{args=[1,2]}',
        ]
        for code in cases:
            with self.subTest(code=code):
                with self.assertRaises(SemanticError):
                    compile_program(code)
                evaluator = compile_program(code, analyze=False)
                with self.assertRaises(EvaluatorError):
                    evaluator.eval_program()
                self.assertEqual(len(evaluator.scope_stack), 1)
                self.assertEqual(evaluator.func_depth, 0)
        for code in ('fn f {a=b,b=1}; end', 'x=9; fn f {a=x,x=1}; end'):
            with self.subTest(code=code), self.assertRaises(SemanticError):
                compile_program(code)

    def test_default_failures_restore_call_state(self):
        for code in (
            'fn f {x=1/0}; return x; end; f{}',
            'fn f {x=f{}}; return x; end; f{}',
            'fn f args {x=1/0}; end; f{1,2}',
        ):
            with self.subTest(code=code):
                evaluator = compile_program(code)
                with self.assertRaises(EvaluatorError):
                    evaluator.eval_program()
                self.assertEqual(len(evaluator.scope_stack), 1)
                self.assertEqual(evaluator.loop_depth, 0)
                self.assertEqual(evaluator.func_depth, 0)
        evaluator = compile_program('x=9; fn f {a=x,x=1}; end; f{}', analyze=False)
        with self.assertRaisesRegex(EvaluatorError, 'read before binding'):
            evaluator.eval_program()
        self.assertEqual(len(evaluator.scope_stack), 1)

    def test_collection_boundary_regressions(self):
        cases = [
            ('a=["hi",1]; d=dict{"a",a}; [d["a"][1],b]=a; print{b+"!"}', 'hi!\n'),
            ('a=["hi",1]; fn get args; a[1]="hi"; return a; end; '
             '[get{}[0],b]=a; print{b+"!"}', 'hi!\n'),
            ('print{len{dict{set{1,1,2}}},len{dict{set{true,1,2}}}}', '1 1\n'),
            ('print{sort{[]},sort{set{}}}', '[] []\n'),
            ('data P [x]; p=P{1}; print{min{[p]}==p,max{[p]}==p}', 'True True\n'),
        ]
        for code, expected in cases:
            with self.subTest(code=code):
                self.assert_output(code, expected)

    def test_for_destructuring_patterns_match_assignment_rules(self):
        cases = (
            ('results=[["Ada",10],["Lin",20]]; '
             'for [name,score] results; print{name,score}; end', 'Ada 10\nLin 20\n'),
            ('for [a,[b,c]] [[1,[2,3,9]],[4,[5,6],7]]; print{a,b,c}; end',
             '1 2 3\n4 5 6\n'),
            ('for [\n name,\n [score,bonus],\n] (\n'
             ' [["Ada",[10,2]],["Lin",[20,3]]]\n)\nprint{name,score+bonus}\nend',
             'Ada 12\nLin 23\n'),
            ('for [] [[],[1],[2,3]]; print{1}; end; '
             'for [a,b] []; print{a,b}; end', '1\n1\n1\n'),
            ('for [x,x] [[1,2],[3,4]]; print{x}; end', '2\n4\n'),
            ('a=[0]; b=[0]; for [x,x[0]] [[a,3],[b,4]]; end; print{a,b}',
             '[3] [4]\n'),
        )
        for code, expected in cases:
            with self.subTest(code=code):
                self.assert_output(code, expected)

    def test_for_destructuring_evaluates_bound_once_and_targets_in_order(self):
        cases = (
            ('fn rows args; print{"rows"}; return [[1,2],[3,4]]; end; '
             'fn slot args; print{"slot"}; return 0; end; '
             'data Box [x]; box=Box{0}; xs=[0]; '
             'for [box.x,xs[slot{}]] rows{}; print{box.x,xs[0]}; end',
             'rows\nslot\n1 2\nslot\n3 4\n'),
            ('row=["hi",1]; for [row[1],value] [row]; print{value+"!"}; end', 'hi!\n'),
            ('row=["hi",1]; fn touch args; print{"touch"}; row[1]="hi"; return row; end; '
             'for [touch{}[0],value] [row]; print{value+"!"}; end', 'touch\nhi!\n'),
            ('rows=[[1,2],[3,4]]; for [rows,x] rows; print{rows,x}; end; print{rows}',
             '1 2\n3 4\n3\n'),
        )
        for code, expected in cases:
            with self.subTest(code=code):
                self.assert_output(code, expected)

    def test_for_destructuring_preserves_scope_and_control_flow(self):
        cases = (
            ('a=9; b=9; for [a,b] [[1,2],[3,4]]; end; print{a,b}', '3 4\n'),
            ('total=0; for [a,b] [[0,9],[1,2],[2,3],[3,4]]; '
             'if a==0; continue; end; if a==3; break; end; total+=a+b; end; print{total}',
             '8\n'),
            ('fn find args; for [name,score] args[0]; if score>10; return name; end; end; '
             'return "none"; end; print{find{[["Ada",10],["Lin",20]]}}', 'Lin\n'),
            ('for [a,b] [[1,2]]; for [a,c] [[3,4]]; print{a,b,c}; end; print{a,b}; end',
             '3 2 4\n3 2\n'),
            ('fns=[]; for [a,b] [[1,2],[3,4]]; fn get args; return [a,b]; end; '
             'fns += [get]; end; print{fns[0]{},fns[1]{}}', '[3, 4] [3, 4]\n'),
            ('value=1; for [value,unused] [[2,0],["s",0]]; end; print{value+"!"}', 's!\n'),
        )
        for code, expected in cases:
            with self.subTest(code=code):
                evaluator = self.assert_output(code, expected)
                self.assertEqual(evaluator.func_depth, 0)
        for code in (
            'for [a,b] [[1,2]]; end; print{a}',
            'a=0; for [a,b] [[1,2]]; end; print{b}',
            'for [missing[0],x] [[1,2]]; end',
            'xs=[0]; for [xs[missing],x] [[1,2]]; end',
            'for [rows,x] rows; end',
        ):
            with self.subTest(code=code), self.assertRaises(SemanticError):
                compile_program(code)

    def test_for_destructuring_failures_restore_loop_and_function_state(self):
        cases = (
            'for [a,b] [1]; end',
            'for [a,b] [[1]]; end',
            'for [a,[b]] [[1,[]]]; end',
            'for [a,[b]] [[1,"x"]]; end',
            'for [] [1]; end',
            'xs=[0]; for [xs[5],b] [[1,2]]; end',
            'data Box [x]; box=Box{}; for [box.y,b] [[1,2]]; end',
            'fn bad args; for [a,b] [[1]]; end; end; bad{}',
        )
        for code in cases:
            with self.subTest(code=code):
                evaluator = compile_program(code)
                with self.assertRaises(EvaluatorError):
                    evaluator.eval_program()
                self.assertEqual(len(evaluator.scope_stack), 1)
                self.assertEqual(evaluator.loop_depth, 0)
                self.assertEqual(evaluator.func_depth, 0)
        evaluator = compile_program(
            'a=0; b=0; count=0; for [a,[b]] [[1,[2]],[3,[]]]; count+=1; end'
        )
        with self.assertRaisesRegex(EvaluatorError, 'not enough values to unpack'):
            evaluator.eval_program()
        self.assertEqual([evaluator.scope_stack[0][name] for name in ('a', 'b', 'count')], [3, 2, 1])
        self.assertEqual(len(evaluator.scope_stack), 1)
        self.assertEqual(evaluator.loop_depth, 0)

    def test_named_and_anonymous_short_function_interfaces(self):
        cases = (
            ('fn power {x} return x*x; fn first args return args[0]; '
             'fn total args {offset=0} return sum{args}+offset; '
             'print{power{5},first{9,8},total{1,2,offset=4}}', '25 9 7\n'),
            ('power=fn {x} return x*x; first=fn args return args[0]; '
             'total=fn args {offset=0} return sum{args}+offset; '
             'print{power{x=5},first{9,8},total{1,2,offset=4}}', '25 9 7\n'),
            ('fn options {x=2} return x; f=fn options {x=2} return [options,x]; '
             'print{options{},f{1,2,x=3}}', '2 [[1, 2], 3]\n'),
            ('fn apply {f,x} return f{x}; '
             'handlers=[fn {x} return x+1,fn {x} return x*2]; '
             'data Box [f]; box=Box{fn {x} return x+3}; '
             'mapping=dict{"square",fn {x} return x*x}; '
             'print{apply{fn {x} return x*x,5},handlers[0]{4},handlers[1]{4},'
             'box.f{4},mapping["square"]{3}}', '25 5 8 7 9\n'),
            ('fn power {\n x,\n factor=1,\n} return (\n x*x*\n factor\n)\n'
             'f=fn {\n x,\n} return (\n x+\n 1\n)\n'
             'print{\n power{\n 3,\n factor=2,\n},\n'
             '(fn args return sum{args}){\n 4,\n 5,\n},\n f{2},\n}', '18 9 3\n'),
        )
        for code, expected in cases:
            with self.subTest(code=code):
                self.assert_output(code, expected)

    def test_short_functions_reuse_closures_defaults_and_recursion(self):
        cases = (
            ('fn mark {label,value}; print{label}; return value; end; '
             'f=fn {x=mark{"default",3}} return mark{"body",x}; print{"made"}; '
             'print{f{x=mark{"arg",5}},f{}}', 'made\narg\nbody\ndefault\nbody\n5 3\n'),
            ('fn bump {xs}; xs[0]+=1; return xs[0]; end; '
             'f=fn {xs=[0]} return bump{xs}; shared=[0]; '
             'print{f{},f{},f{shared},f{shared}}', '1 1 1 2\n'),
            ('x=2; f=fn {a=x,b=a+1} return [a,b,x]; x=7; print{f{},f{0},x}',
             '[7, 8, 7] [0, 1, 7] 7\n'),
            ('fn make {x} return fn {y=1} return x+y; a=make{2}; b=make{7}; '
             'print{a{},a{3},b{},b{0}}', '3 5 8 7\n'),
            ('fn factory args; n=[0]; fn tick ignored; n[0]+=1; return n[0]; end; '
             'return fn {} return tick{}; end; a=factory{}; b=factory{}; '
             'print{a{},a{},b{}}', '1 2 1\n'),
            ('x=1; fn move args; x=2; return 0; end; '
             'print{(fn {v} return x){move{}}}', '2\n'),
            ('fn fact {n} return (n<=1 && 1) || n*fact{n-1}; '
             'other=fn {n} return (n<=1 && 1) || n*other{n-1}; '
             'print{fact{6},other{6}}', '720 720\n'),
            ('fn invoke {f=fn {x} return x+1,x=4} return f{x}; print{invoke{}}', '5\n'),
            ('a=fn {} return 1; b=a; c=fn {} return 1; print{a==b,a==c}', 'True False\n'),
        )
        for code, expected in cases:
            with self.subTest(code=code):
                evaluator = self.assert_output(code, expected)
                self.assertNotIn(None, evaluator.scope_stack[0])
                self.assertEqual(evaluator.func_depth, 0)

    def test_short_functions_respect_expression_and_block_boundaries(self):
        cases = (
            ('fn outer args; for [x,y] [[1,2],[3,4]]; fn scale {z} return z*2; '
             'if x==3; return (fn {v} return scale{v}+y){x}; end; end; return 0; end; '
             'print{outer{}}', '10\n'),
            ('fs=[]; for value [1,2]; fs += [fn {} return value]; end; '
             'print{fs[0]{},fs[1]{}}', '2 2\n'),
            ('print{(fn {} return 1+2*3){},(fn {x} return -x*2){3},'
             '(fn {} return [1,sum{[2,3]}]){}[1],'
             '((fn {x} return fn {y} return x+y){3}){4}}', '7 -6 5 7\n'),
            ('fn outer args; unused=fn {} return 99; return 1; end; print{outer{}}', '1\n'),
            ('f=fn {} return 1/0; print{"created"}', 'created\n'),
            ('fn a {x}; return x+1; end; fn b {x} return a{x}+1; '
             'fn c {x}; return b{x}+1; end; print{c{1}}', '4\n'),
        )
        for code, expected in cases:
            with self.subTest(code=code):
                evaluator = self.assert_output(code, expected)
                self.assertEqual(evaluator.func_depth, 0)

    def test_slice_reads_use_exclusive_clamped_bounds_and_shallow_copies(self):
        cases = (
            ('values=[0,1,2,3,4,5]; print{values[1:5],values[::-1],values[::2]}',
             '[1, 2, 3, 4] [5, 4, 3, 2, 1, 0] [0, 2, 4]\n'),
            ('a=[0,1,2,3]; print{a[-3:-1],a[-99:99],a[99:],a[3:1],'
             'a[:-1:-1],a[3:0:-2],a[::true],a[none:2],[][::2]}',
             '[1, 2] [0, 1, 2, 3] [] [] [] [3, 1] [0, 1, 2, 3] [0, 1] []\n'),
            ('print{"abcdef"[1:5:2],"café🙂"[::-1],""[:],[[1,2],[3,4]][1:][0][::-1]}',
             'bd 🙂éfac  [4, 3]\n'),
            ('a=[[1],[2]]; b=a[:]; b[0][0]=9; b[1]=[8]; print{a,b}',
             '[[9], [2]] [[9], [8]]\n'),
            ('a=[0,1,2,3]; print{a[\n 1:\n 4:\n 2\n]}', '[1, 3]\n'),
        )
        for code, expected in cases:
            with self.subTest(code=code):
                self.assert_output(code, expected)

    def test_slice_assignments_preserve_aliases_and_validate_extended_lengths(self):
        cases = (
            ('a=[0,1,2,3]; b=a; a[1:3]=[9]; a[1:1]=[7,8]; '
             'a[-1:]=[]; print{a,b}', '[0, 7, 8, 9] [0, 7, 8, 9]\n'),
            ('a=[0,1,2,3,4]; a[::2]=[9,8,7]; print{a}; a[::-1]=a; print{a}',
             '[9, 1, 8, 3, 7]\n[7, 3, 8, 1, 9]\n'),
            ('a=[1,2,3]; a[1:2]+=[8]; print{a}; a[0:2]*=2; print{a}',
             '[1, 2, 8, 3]\n[1, 1, 2, 2, 8, 3]\n'),
            ('a=[1,2]; a[:]=a; a[1:1]=a; print{a}', '[1, 1, 2, 2]\n'),
            ('a=[1]; a[:]=["ok"]; print{a[0]+"!"}', 'ok!\n'),
            ('a=[[1],[2]]; for [a[:],value] [[[3,4],9]]; print{a,value}; end',
             '[3, 4] 9\n'),
        )
        for code, expected in cases:
            with self.subTest(code=code):
                self.assert_output(code, expected)

    def test_slice_expressions_evaluate_once_in_existing_assignment_order(self):
        self.assert_output(
            'a=[0,1,2,3]; fn base args; print{"base"}; return a; end; '
            'fn mark {label,value}; print{label}; return value; end; '
            'print{base{}[mark{"start",0}:mark{"stop",4}:mark{"step",2}]}; '
            'base{}[mark{"target",1}:3]=mark{"rhs",[9]}; '
            'base{}[mark{"target",1}:2]+=mark{"rhs",[8]}; print{a}',
            'base\nstart\nstop\nstep\n[0, 2]\nrhs\nbase\ntarget\n'
            'base\ntarget\nrhs\n[0, 9, 8, 3]\n',
        )

    def test_slice_errors_are_checked_statically_and_dynamically(self):
        for code in (
            'a=[1,2]; a[::0]', 'a=[1,2]; a[::false]', 'a=[1,2]; a[::none]',
            'a=[1,2]; a[1.0:]', 'a=[1,2]; a[:"x"]', 'a=[1,2]; a[::[]]',
            'dict{}[:]', 'set{}[:]', 'a=1; a[:]', 'a=[1,2]; a[:]=1',
            'a=[1,2]; a[::2]=[]', 'a="abc"; a[:]=[1]',
        ):
            with self.subTest(code=code):
                with self.assertRaises(SemanticError):
                    compile_program(code)
                evaluator = compile_program(code, analyze=False)
                with self.assertRaises(EvaluatorError):
                    evaluator.eval_program()
                self.assertEqual(len(evaluator.scope_stack), 1)
        evaluator = compile_program(
            'a=[1,2]; fn replace {value}; a[::2]=value; end; replace{[]}'
        )
        with self.assertRaises(EvaluatorError):
            evaluator.eval_program()
        self.assertEqual(evaluator.scope_stack[0]['a'], [1, 2])
        self.assertEqual(len(evaluator.scope_stack), 1)
        self.assertEqual(evaluator.func_depth, 0)

    def test_interpolated_strings_compose_with_bang_expressions_and_escapes(self):
        cases = (
            ('name="Ada"; score=42; print{f"{name} scored {score} points"}',
             'Ada scored 42 points\n'),
            ('x=3; print{f"{{{x}}}","{x}",f"{{}}",f"",f"no fields"}',
             '{3} {x} {}  no fields\n'),
            ('values=[1,2,3,4]; print{f"{sum{values[1::2]}}:{len{"ab"}}"}', '6:2\n'),
            ('x=4; print{f"outer {f"inner {x}"}"}', 'outer inner 4\n'),
            ('print{f"{(fn {x} return x*x){3}} {dict{"a",1}} {1<2} {none}"}',
             "9 {'a': 1} True 0\n"),
            (r'print{"a\nb",f"say \"hi\"\\{2}","\q"}', 'a\nb say "hi"\\2 \\q\n'),
            ('fn label {x,text=f"value={x}"} return text; print{label{3},label{4,"custom"}}',
             'value=3 custom\n'),
        )
        for code, expected in cases:
            with self.subTest(code=code):
                self.assert_output(code, expected)

    def test_interpolation_fields_evaluate_and_format_once_from_left_to_right(self):
        self.assert_output(
            'a=[1,2]; n=0; fn change args; n+=1; a[0]=9; return n; end; '
            'print{f"{a}|{change{}}|{a}|{change{}}"}; print{n}',
            '[1, 2]|1|[9, 2]|2\n2\n',
        )
        evaluator = compile_program(
            'n=0; fn fail args; return 1/0; end; fn later args; n+=1; return n; end; '
            'fn outer args; for i 1; return f"{fail{}} {later{}}"; end; end; outer{}'
        )
        with self.assertRaises(EvaluatorError):
            evaluator.eval_program()
        self.assertEqual(evaluator.scope_stack[0]['n'], 0)
        self.assertEqual(len(evaluator.scope_stack), 1)
        self.assertEqual(evaluator.func_depth, 0)
        self.assertEqual(evaluator.loop_depth, 0)

    def test_slice_and_interpolation_cli_errors_point_into_the_original_source(self):
        cases = (
            ('\nprint{\n  f"value={missing}"\n}', 3, 3, 'variable not initialized'),
            ('\nprint{\n  f"value={1+}"\n}', 2, 3, 'operand'),
            ('fn zero args; return 0; end\nprint{\n  f"value={1/zero{}}"\n}',
             4, 3, 'zero'),
            ('\nprint{\n  f"{[1,2][::0]}"\n}', 3, 3, 'slice step'),
            ('\nprint{\n  f"bad }"\n}', 1, 3, "single '}'"),
        )
        for code, status, row, message in cases:
            with self.subTest(code=code), tempfile.TemporaryDirectory() as directory:
                source = Path(directory) / 'program.bang'
                source.write_text(code, encoding='utf-8')
                diagnostic = io.StringIO()
                with contextlib.redirect_stderr(diagnostic):
                    self.assertEqual(run_file(str(source)), status)
                text = diagnostic.getvalue()
                self.assertIn(f'Line {row},', text)
                self.assertIn(message, text)
                self.assertIn(code.splitlines()[row - 1].strip(), text)
                self.assertNotIn('Traceback', text)

    def test_short_function_errors_preserve_binding_checks_and_scope_cleanup(self):
        for code in (
            'fn f {x} return x; f{}', 'f=fn {} return 1; f{1}',
            '(fn {x} return x){other=1}', 'f=fn args return 0; f{x=1}',
            'f=fn args {offset} return offset; f{1,2}',
            'fn f {x} return x; f{1,x=2}',
        ):
            with self.subTest(code=code):
                with self.assertRaises(SemanticError):
                    compile_program(code)
                evaluator = compile_program(code, analyze=False)
                with self.assertRaises(EvaluatorError):
                    evaluator.eval_program()
                self.assertEqual(len(evaluator.scope_stack), 1)
                self.assertEqual(evaluator.loop_depth, 0)
                self.assertEqual(evaluator.func_depth, 0)
        for code in (
            'f=fn {x=missing} return x', 'f=fn {x=y,y=1} return x',
            'f=fn {x=x} return x', 'f=fn {} return missing',
        ):
            with self.subTest(code=code), self.assertRaises(SemanticError):
                compile_program(code)
        for code in (
            'f=fn {x=1/0} return x; f{}', 'f=fn {x} return 1/x; f{0}',
            'fn bad {x} return 1/x; bad{0}',
            'fn outer args; for i 1; return (fn {} return 1/0){}; end; end; outer{}',
            'f=fn {self} return self{self}; f{f}',
            'f=fn {x=f{}} return x; f{}',
        ):
            with self.subTest(code=code):
                evaluator = compile_program(code)
                with self.assertRaises(EvaluatorError):
                    evaluator.eval_program()
                self.assertEqual(len(evaluator.scope_stack), 1)
                self.assertEqual(evaluator.loop_depth, 0)
                self.assertEqual(evaluator.func_depth, 0)


if __name__ == "__main__":
    unittest.main()
