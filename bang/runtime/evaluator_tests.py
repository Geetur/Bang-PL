import pytest

from bang.lexing.lexer import Lexer
from bang.parsing.control_flow_parser import ControlFlowParser
from bang.parsing.expression_parser import ExpressionParser
from bang.runtime.evaluator import Evaluator, EvaluatorError
from bang.semantic.semantic_analysis import SemanticAnalysis


def evaluate(code: str, tmp_path):
    """Tokenises, parses, semantically analyses **and** executes a small Bang
    program.  Any *EvaluatorError* raised at run-time will bubble up to the test
    layer just like *SemanticError* does in the compile-time suite.
    """
    src = tmp_path / "temp.bang"
    src.write_text(code)

    # ---------- LEX + PARSE ----------
    lexer = Lexer(str(src))
    tokens = lexer.tokenizer()

    e_parser = ExpressionParser(tokens, lexer.file)
    e_parser.split()
    e_parser.loading_into_algos()

    cf_parser = ControlFlowParser(lexer.file, e_parser.post_SYA)
    roots = cf_parser.blockenize()

    # ---------- SEMANTIC CHECK ----------
    sema = SemanticAnalysis(lexer.file, roots)
    sema.walk_program()  # will raise on failure

    # ---------- EVALUATION (unit under test) ----------
    runner = Evaluator(lexer.file, roots)
    runner.eval_program()  # may raise EvaluatorError
    return runner  # returned so tests can poke at state if they wish


# ----------------------------
# Positive test‑cases (should *not* raise)
# ----------------------------
@pytest.mark.parametrize(
    "program",
    [
        # Simple arithmetic & variable propagation
        "x = 1\ny = 2\nz = x + y\n",
        "x = 1\ny = true\nz = x + y\n",
        "x = 1\ny = false\nz = x + y\n",
        # array arithmetic
        "x = [1]\ny = [2]\nz = x + y\n",
        "x = [1,2]\ny = [2]\nz = x - y\n",
        "x = [1]\ny = 2\nz = x * y\n",
        "x = [1]\ny = [2]\nz = x * y\n",
        "x = [1,2,3]\ny = [2]\nz = x / y\n",
        "x = 2\ny = [1]\nz = x * y\n",
        "x = [1]\ny = [2]\nx += y\n",
        "x = [1,2]\ny = [2]\nx -= y\n",
        "x = [1]\ny = 2\nx *= y\n",
        "x = [1]\ny = [2]\nx *= y\n",
        "x = [1,2,3]\ny = [2]\nx /= y\n",
        "x = 2\ny = [1]\nx *= y\n",
        # string arithmetic
        'x = "12"\ny = "2"\nz = x - y\n',
        'x = "1,2"\ny = ","\nz = x / y\n',
        'x = "1"\ny = 2\nz = x * y\n',
        'x = 1\ny = "2"\nz = x * y\n',
        'x = "12"\ny = "2"\nx -= y\n',
        'x = "1,2"\ny = ","\nx /= y\n',
        'x = "1"\ny = 2\nx *= y\n',
        'x = 1\ny = "2"\nx *= y\n',
        'x = ["1"]\ny = ["2"]\nx[0] += y[0]\n',
        'x = ["1"]\n y = ["2"]\n x[0] -= y[0]\n',
        'x = ["1"]\ny = 2\nx[0] *= y\n',
        'x = ["1"]\ny = [2]\nx[0] *= y[0]\n',
        'x = ["1,2,3"]\ny = ["2"]\nx[0] /= y[0]\n',
        'x = "2"\ny = [1]\nx *= y[0]\n',
        # indexing
        "arr = [10, 20, 30]\nidx = 1\nval = arr[idx]\n",
        "dict{1,2}[1]\n",
        # Function definition & call
        "fn add args\n return args[0] + args[1]\nend\nresult = add{2,3}\n",
        # Boolean logic evaluated at run‑time
        "flag = true\nother = false\nres = flag && !other\n",
        # built in sum function
        "sum{[1,2,3,4]}\n",
        "sum{[1,2,false,true]}\nsum{[[1],[2],[3],[4]]}\n",
        "sum{[1,2,3,4]}\n",
        'sum{["1","2","3","4"]}\n',
        'sum{["12","3","4"]}\n',
        "print{sum{[dict{1, 2}, dict{2, 3}, dict{4, 5}]}}\n",
        "print{sum{[set{[1, 2]}, set{[2, 3]}, set{[4, 5]}]}}\n",
        'sum{"1","2","3","4"}\n',
        "sum{1,2,3,4}\n",
        "print{sum{dict{1, 2}, dict{2, 3}, dict{4, 5}}}\n",
        "print{sum{set{[1, 2]}, set{[2, 3]}, set{[4, 5]}}}\n",
        "data Class [rand]; class = Class{1}; sum{1,2,class.rand}\n",
        'data Class [rand]; class = Class{"1"}; sum{"1","2",class.rand}\n',
        "data Class [rand]; class = Class{[1,2,3]}; sum{class.rand}\n",
        "data Class [rand]; class = Class{dict{1,2}}; sum{dict{3,4},dict{4,5},class.rand}\n",
        "data Class [rand]; class = Class{set{1,2,3}}; sum{class.rand}\n",
        # built in min function
        "min{[1,2,3,4]}\n",
        "min{[1,2,false,true]}\nmin{[[1],[2],[3],[4]]}\n",
        "min{[1,2,3,4]}\n",
        'min{["1","2","3","4"]}\n',
        "min{1,2,3,4}\n",
        "min{1,2,false,true}\nmin{[1],[2],[3],[4]}\n",
        'min{"1","2","3","4"}\n',
        "data Class [rand]; class = Class{1}; min{1,2,class.rand}\n",
        'data Class [rand]; class = Class{"1"}; min{"1","2",class.rand}\n',
        "data Class [rand]; class = Class{[1,2,3]}; min{class.rand}\n",
        "data Class [rand]; class = Class{[1,2]}; min{[3,4],[4,5],class.rand}\n",
        "data Class [rand]; class = Class{set{1,2,3}}; min{class.rand}\n",
        # built in max function
        "max{[1,2,3,4]}\n",
        "max{[1,2,false,true]}\n",
        "max{[[1],[2],[3],[4]]}\n",
        'max{["1","2","3","4"]}\n',
        "max{1,2,3,4}\n",
        "max{1,2,false,true}\n",
        "max{[1],[2],[3],[4]}\n",
        'max{"1","2","3","4"}\n',
        "data Class [rand]; class = Class{1}; max{1,2,class.rand}\n",
        'data Class [rand]; class = Class{"1"}; max{"1","2",class.rand}\n',
        "data Class [rand]; class = Class{[1,2,3]}; max{class.rand}\n",
        "data Class [rand]; class = Class{[1,2]}; max{[3,4],[4,5],class.rand}\n",
        "data Class [rand]; class = Class{set{1,2,3}}; max{class.rand}\n",
        # built in len function
        "len{[1,2,3,4,5]}\n",
        'len{[1,2,3,4,"5"]}\n',
        "len{[1,2,3,4,[5]]}\n",
        'len{"12fgdgd"}\n',
        "data Class [rand]; class = Class{[1,2,3]}; len{class.rand}\n",
        "data Class [rand]; class = Class{set{1,2,3}}; len{class.rand}\n",
        "data Class [rand]; class = Class{dict{1,2,3,4,5,6}}; len{class.rand}\n",
        'data Class [rand]; class = Class{"hjdfghjlfgdhjdfg"}; len{class.rand}\n',
        # built in print function
        "print{[1,2,3,4,5]}\n",
        "print{1,2,3,4,5}\n",
        "print{[1,2,3,4,5], 1}\n",
        'print{[1,2,3,4,5], "1"}\n',
        'print{"ffsfsfsfs"}\n',
        "print{true, false}\n",
        'print{"ffsfsfsfs"}\n',
        'x = "12"\ny = 2\nz = true\n print{x,y,z}\n',
        "x = [[0] * 5] * 5\nprint{x}\n",
        'print{["sfdsdffsfsd", 1, false, true, ["hello"]]}\n',
        "print{set{[1,2,3]}}\n",
        "print{dict{1,2}}\n",
        "print{dict{1,2,2,3,4,5}}\n",
        "data Class [rand]; class = Class{[1,2,3]}; print{class.rand}\n",
        "data Class [rand]; class = Class{set{1,2,3}}; print{class.rand}\n",
        "data Class [rand]; class = Class{dict{1,2,3,4,5,6}}; print{class.rand}\n",
        'data Class [rand]; class = Class{"hjdfghjlfgdhjdfg"}; print{class.rand}\n',
        "data Class [rand]; class = Class{dict}; print{class.rand}\n",
        # built in sort function
        "sort{[1,2, 3]}\n",
        "sort{[[1,2, 3], [1,2,4]]}\n",
        'sort{["1","2", "3"]}\n',
        'sort{["323425232353456"]}\n',
        "sort{[1,true, false]}\n",
        "sort{1,2, 3}\n",
        "sort{[1,2, 3], [1,2,4]}\n",
        'sort{"1","2", "3"}\n',
        'sort{"323425232353456"}\n',
        "sort{1,true, false}\n",
        "data Class [rand]; class = Class{[1,2,3]}; sort{class.rand}\n",
        "data Class [rand]; class = Class{set{1,2,3}}; sort{class.rand}\n",
        "data Class [rand]; class = Class{dict{1,2,3,4,5,6}}; sort{class.rand}\n",
        'data Class [rand]; class = Class{"hjdfghjlfgdhjdfg"}; sort{class.rand}\n',
        # built in set function
        'set{[1,2, "5"]}\n',
        "set{[1,2, 4]}\n",
        "set{[1,2, true]}\n",
        "set{[1,2, false]}\n",
        "set{}\n",
        'set{1,2, "5"}\n',
        "set{1,2, 4}\n",
        "set{1,2, true}\n",
        "set{1,2, false}\n",
        "set{1}\n",
        'set{"1"}\n',
        "set{false}\n",
        "a= set{[1,2, 4]} + set{[1,6,7]}\n",
        "a= set{} + set{[1,6,7]}\n",
        "a= set{[1,2, 4]} - set{[1,6,7]}\n",
        "a= set{[1,2, 4]} - set{}\n",
        "a= set{[1,2, 4]} > set{[1,6,7]}\n",
        "a= set{} >= set{[1,6,7]}\n",
        "a= set{[1,2, 4]} < set{1,6,7}\n",
        "a= set{[1,2, 4]} <= set{}\n",
        "a= set{[1,2, 4]} == set{1,6,7}\n",
        "a= set{} != set{1,6,7}\n",
        "a= set{[1,2, 4]} && set{1,6,7}\n",
        "a= set{[1,2, 4]} || set{}\n",
        "data Class [rand]; class = Class{[1,2,3]}; set{class.rand}\n",
        "data Class [rand]; class = Class{set{1,2,3}};\n",
        'data Class [rand]; class = Class{"hjdfghjlfgdhjdfg"}; set{class.rand}\n',
        "data Class [rand]; class = Class{[1,2,3]}; set{(class.rand + [1,2,3,4,5]) * 3}\n",
        # built in dict function
        "dict{1,2}\n",
        "dict{1,false}\n",
        'dict{1,"2"}\n',
        "dict{1,[3]}\n",
        "dict{1,set{[1]}}\n",
        "dict{1,dict{1, 2}}\n",
        'dict{[1,dict{1, 2}, 1, 2, 2, set{1}, 9, false, 10, "hi"]}\n',
        "dict{}\n",
        "dict{1,2} + dict{[3,2]}\n",
        "dict{1,2} + dict{[1,2]}\n",
        "dict{1,2} + dict{}\n",
        "dict{1,2} - dict{[3,2]}\n",
        "dict{1,2} - dict{[1,2]}\n",
        "dict{1,2} - dict{[]}\n",
        "dict{1,2} == dict{3,2}\n",
        "dict{1,2} != dict{1,2}\n",
        "dict{1,2} && dict{}\n",
        "dict{1,2} || dict{3,2}\n",
        "data Class [rand]; class = Class{[1,2,3,4]}; dict{class.rand}\n",
        "data Class [rand]; class = Class{[1,[1],2, [2]]}; dict{class.rand}\n",
        # built in range function
        "range{9}\n",
        "range{1, 9}\n",
        "range{1, 9, 2}\n",
        "range{[1, 9, 2]}\n",
        "range{9, 9, 2}\n",
        "range{9, 1, -1}\n",
        "x = [1,2,3]; range{len{x}, -1, -1}\n",
        "x = [1,2,3]; range{len{x}}\n",
        "print{range{9}}\n",
        "range{1, 9, true}\n",
        "range{9} + range{7}\n",
        "range{9} * 4\n",
        "range{9} / [2]\n",
        "range{9} * [4]\n",
        "range{9} - [1,2]\n",
        "data Class [rand]; class = Class{[1, 9, 2]}; range{class.rand}\n",
        "data Class [rand]; class = Class{[0, 10, -1]}; range{class.rand}\n",
        "data Class [rand]; class = Class{1}; range{class.rand, 10}\n",
        # for loops
        "for i range{9}; end\n",
        "for i range{1, 10}; end\n",
        "for i range{1, 10, 2}; end\n",
        "x = [1,2,3]; for i range{len{x}}; end\n",
        "x = [1,2,3]; for i range{1, len{x}}; end\n",
        "x = [1,2,3]; for i range{len{x}, -1, -1}; end\n",
        "x = [1,2,3]; for i range{len{x}, -1, -1}; print{i}; end\n",
        "x = [1,2,3]; for i range{len{x}, -1, -1}; i += 1; end\n",
        "for i 9; i += 1; end;\n",
        "for i -9; i += 1; end\n",
        "x = [1,2,3]; for i x; i += 1; end\n",
        "x = set{[1,2,3,4,5]}; for i x; i += 1; end\n",
        "x = dict{1,2}; for i x; end\n",
        "data Class [rand]; class = Class{[0, 10, -1]}; for i class.rand; i += 1; end\n",
        # in operator
        "fn bar args\n return 5\nend\nbar{} in [1]\n",
        'fn bar args\n return "5"\nend\nbar{} in "5"\n',
        'fn bar args\n return "5"\nend\nbar{} in [true]\n',
        "fn bar args\n return [5]\nend\nbar{} in [5]\n",
        "fn bar args\n return true\nend\nbar{} in [1]\n",
        "data Class [rand]; class = Class{[0, 10, -1]}; 0 in class.rand\n",
        # multivariable assignment
        "fn bar args\n return [5]\nend\n[hello] = bar{}\n",
        "fn bar args\n return [true]\nend\n[hello] = bar{}\n",
        'fn bar args\n return ["5"]\nend\n[hello] = bar{}\n',
        "fn bar args\n return [[4]]\nend\n[hello] = bar{}\n",
        'fn bar args\n return ["5", "4"]\nend\n[hello, dict{5, "place_holder"}[5]] = bar{}\n',
        "fn bar args\n return [[4], [1, 2]]\nend\n[hello, [x, y]] = bar{}\n",
        'fn bar args\n return ["5", "4"]\nend\n[hello, [1, 2][1]] = bar{}\n',
        "fn bar args\n return [5]\nend\n hello = 5\n [hello] += bar{}\n",
        "fn bar args\n return [true]\nend\n hello = 5\n[hello] += bar{}\n",
        'fn bar args\n return ["5"]\nend\n hello = "5"\n[hello] += bar{}\n',
        "fn bar args\n return [[4]]\nend\n hello = [5]\n[hello] += bar{}\n",
        "fn bar args\n return [5]\nend\n hello = 5\n [hello] -= bar{}\n",
        "fn bar args\n return [true]\nend\n hello = 5\n[hello] -= bar{}\n",
        'fn bar args\n return ["5"]\nend\n hello = "5"\n[hello] -= bar{}\n',
        "fn bar args\n return [[4]]\nend\n hello = [5]\n[hello] -= bar{}\n",
        "fn bar args\n return [5]\nend\n hello = 5\n [hello] *= bar{}\n",
        "fn bar args\n return [true]\nend\n hello = 5\n[hello] *= bar{}\n",
        'fn bar args\n return [5]\nend\n hello = "5"\n[hello] *= bar{}\n',
        "fn bar args\n return [[4]]\nend\n hello = [5]\n[hello] *= bar{}\n",
        "fn bar args\n return [4]\nend\n hello = [5]\n[hello] *= bar{}\n",
        "fn bar args\n return [5]\nend\n hello = 5\n [hello] /= bar{}\n",
        "fn bar args\n return [true]\nend\n hello = 5\n[hello] /= bar{}\n",
        'fn bar args\n return ["5"]\nend\n hello = "5"\n[hello] /= bar{}\n',
        "fn bar args\n return [[4]]\nend\n hello = [5]\n[hello] /= bar{}\n",
        "data Class [rand]; class = Class{[0, 10, -1]}; class.rand[0] = 4\n",
        "data Class [rand]; class = Class{}; [[1,2,3,4][0], class.rand] = [1, 2]\n",
        "data Class [rand, rand2]; class = Class{}; [class.rand, class.rand2] = [1, 2]\n",
        # weird function calls
        "fn foo args\n return dict\nend\nx = foo{}{1,2}\n",
        "fn foo args\n return dict\nend\nx = foo{}{1,2, 3,4, 5, 6}\n",
        "fn foo args\n return set\nend\nx = foo{}{[1,2]}\n",
        'fn foo args\n return len\nend\nx = foo{}{"123456hi"}\n',
        'fn foo args\n return [len]\nend\nx = foo{}[0]{"123456hi"}\n',
        'fn foo args\n return [[[len]]]\nend\nx = foo{}[0][0][0]{"123456hi"}\n',
        'fn foo args\n return [[[len]]]\nend\n data Class [rand, rand2]; class = Class{foo}; x = class.rand{}[0][0][0]{"123456hi"}\n',
        # shadowing built in set
        "fn set args; return [1,2,3]; end; a = set{}[1]\n",
        "fn set args; return [1,2,3]; end; a = set{dict{1, 2}}\n",
        "fn set args; return [1,2,3]; end; a = set{[[1, 2]]}\n",
        # shadowing built in dict
        "fn dict args; return [1,2,3]; end; a = dict{}[0]\n",
        "fn dict args; return [1,2,3]; end; a = dict{dict{1, 2}}\n",
        "fn dict args; return [1,2,3]; end; a = dict{1}\n",
        # dataclass quality checks and niche cases
        "data B [c]; data A [b]; a = A{B{3}}; print{a.b.c}\n",
        "data P [x,y]; p = P{1}; p.y = 2; print{p.x + p.y}\n",
        "data P [x]; p = P{1}; p.x += 2\n",
        "data P [x]; arr = [P{1}, P{2}]; arr[0].x = 9; print{arr[0].x}\n",
        "data Pair [a,b]; p = Pair{}; [p.a, p.b] = [1, 2]\n",
        "data Pair [a,b]; p = Pair{}; [p.a, [p.b]] = [1, [2]]\n",
        "fn inc args; return args[0] + 1; end; data C [f]; c = C{inc}; print{c.f{41}}\n",
        "data T [len]; t = T{1}; print{t.len}\n",
        "data C [xs]; c = C{[1,2,3]}; set{(c.xs + [4]) * 2}\n",
        "data N [next]; n = N{}; n.next = N{}; n.next.next = N{}\n",
        "data P [x]; p = P{}; [[1,2][0], p.x] = [9, 8]; print{p.x}\n",
    ],
)
def test_evaluator_valid(program, tmp_path):
    """Programs here should *run to completion* with **no EvaluatorError**."""
    evaluate(program, tmp_path)  # will raise on failure


# ----------------------------
# Negative test‑cases (should raise EvaluatorError)
# ----------------------------
@pytest.mark.parametrize(
    "program",
    [
        # Division by zero caught at run‑time
        "x = 5\ny = 0\nz = x / y\n",
        "x = [5]\ny = [0]\nz = x / y\n",
        "x = [5,5,5]\ny = [1,2,0]\nz = x / y\n",
        "data B [z]; b = B{0}; print{1 / b.z}\n",
        "data B [z]; b = B{[1,2,0]}; print{[1,2,3] / b.z}\n",
        # Index out of bounds that was not detectable statically
        "arr = [1]\nidx = 3\nval = arr[idx+5]\n",
        "data B [z]; b = B{[0]}; print{b.z[1+2]}\n",
        # illegal indexing
        "a = [5]\n b = a[0+1]",
        "a = [5, [2]]\n b = a[0+1][3]",
        "fn bar args\n return [1]\nend\nx = [2,3,4][bar{}]\n",
        'fn bar args\n return "5"\nend\nx = [2,3,4][bar{}]\n',
        "a = dict{1,2}\n b = a[0]\n",
        "fn foo args; return set{1,2}; end; b = foo{}[1]\n",
        "fn foo args; return set{1,2}; end; data Class [rand]; class = Class{foo}; b = class.rand{}[1]\n",
        # illegal arithmetic
        "fn bar args\n return 5\nend\nx = bar{} + [2,3,4]\n",
        'fn bar args\n return 5\nend\nx = bar{} + "3"\n',
        'fn bar args\n return "5"\nend\nx = 1 + bar{}\n',
        'fn bar args\n return [1]\nend\nx = "1" + bar{}\n',
        'fn bar args\n return "5"\nend\nx = set{1} + bar{}\n',
        "fn bar args\n return [1]\nend\nx = dict{1,2} + bar{}\n",
        "fn foo args; return set{1,2}; end; data Class [rand]; class = Class{foo}; b = class.rand{} + 1\n",
        "fn bar args; return 5; end; data Class [rand]; fn foo args; return Class{bar}; end; x = foo{}.rand + [2,3,4]\n",
        'fn bar args; return 5; end; data Class [rand]; fn foo args; return Class{bar}; end; x = foo{}.rand + "3"\n',
        'fn bar args;  return "5"; end; data Class [rand]; fn foo args; return Class{bar}; end; x = 1 + foo{}.rand\n',
        'fn bar args; return [1]; end; data Class [rand]; fn foo args; return Class{bar}; end; x = "1" + foo{}.rand\n',
        'fn bar args; return "5"; end; data Class [rand]; fn foo args; return Class{bar}; end; x = set{1} + foo{}.rand\n',
        "fn bar args; return [1]; end; data Class [rand]; fn foo args; return Class{bar}; end; x = dict{1,2} + foo{}.rand\n",
        # illegal built in len
        "len{}\n",
        'len{1,2,3,"4"}\n',
        "len{1,2,3,set{}}\n",
        "len{1,2,3,dict{}}\n",
        "len{1,2,3,[1]}\n",
        "data Class [rand]; class = Class{len}; class.rand{}\n",
        'data Class [rand]; class = Class{len}; class.rand{1,2,3,"4"}\n',
        "data Class [rand]; class = Class{len}; class.rand{1,2,3,set{}}\n",
        "data Class [rand]; class = Class{1}; len{class.rand}\n",
        # illegal built in sum function
        'sum{[1,2,3,"4"]}\n',
        "sum{1,2,3,set{}}\n",
        "sum{1,2,3,dict{}}\n",
        "sum{1,2,3,[1]}\n",
        'data Class [rand]; class = Class{[1,2,3,"4"]}; sum{class.rand}\n',
        "data Class [rand]; class = Class{[1,2,3,set{}]}; sum{class.rand}\n",
        "data Class [rand]; class = Class{[1,2,3,dict{}]}; sum{class.rand}\n",
        "data Class [rand]; class = Class{[1,2,3,[1]]}; sum{class.rand}\n",
        # illegal built in min function
        'min{[1,2,3,"4"]}\n',
        "min{1,2,3,[5]}\n",
        "min{1,2,3,set{}}\n",
        "min{1,2,3,dict{}}\n",
        "min{}\n",
        'data Class [rand]; class = Class{[1,2,3,"4"]}; min{class.rand}\n',
        "data Class [rand]; class = Class{[1,2,3,set{}]}; min{class.rand}\n",
        "data Class [rand]; class = Class{[1,2,3,dict{}]}; min{class.rand}\n",
        "data Class [rand]; class = Class{[1,2,3,[1]]}; min{class.rand}\n",
        # illegal built in max function
        'max{[1,2,3,"4"]}\n',
        "max{1,2,3,[5]}\n",
        "max{1,2,3,set{}}\n",
        "max{1,2,3,dict{}}\n",
        "max{}\n",
        'data Class [rand]; class = Class{[1,2,3,"4"]}; max{class.rand}\n',
        "data Class [rand]; class = Class{[1,2,3,set{}]}; max{class.rand}\n",
        "data Class [rand]; class = Class{[1,2,3,dict{}]}; max{class.rand}\n",
        "data Class [rand]; class = Class{[1,2,3,[1]]}; max{class.rand}\n",
        # illegal built in len function
        "fn foo args; return 1; end; len{foo{}}\n",
        "fn foo args; return false; end; len{foo{}}\n",
        "data Class [rand]; class = Class{1}; len{class.rand}\n",
        "data Class [rand]; class = Class{false}; len{class.rand}\n",
        # illegal built in sort function
        'sort{[1,2, "5"]}\n',
        "sort{[1,2, [5]]}\n",
        "sort{1,2,set{}}\n",
        "sort{1,2,dict{}}\n",
        "sort{}\n",
        'data Class [rand]; class = Class{[1,2, "5"]}; sort{class.rand}\n',
        "data Class [rand]; class = Class{[1,2, [5]]}; sort{class.rand}\n",
        # illegal built in set function
        "fn foo args; return [1,2, [5]]; end; set{foo{}}\n",
        "fn foo args; return [1,2, set{1,2}]; end; set{foo{}}\n",
        "fn foo args; return [1,2, dict{1,2}]; end; set{foo{}}\n",
        "fn foo args; return set{[1,2, 5]}; end; foo{} * foo{}\n",
        "fn foo args; return set{[1,2, 5]}; end; foo{} / set{[1,2, 5]}\n",
        "fn foo args; return set{[1,2, 5]}; end; foo{} // set{[1,2, 5]}\n",
        "fn foo args; return set{[1,2, 5]}; end; foo{} ** set{[1,2, 5]}\n",
        "fn foo args; return set{1,2, 5}; end; 1 + foo{}\n",
        "fn foo args; return set{1,2, 5}; end; false + foo{}\n",
        'fn foo args; return set{1,2, 5}; end; "1" + foo{}\n',
        "fn foo args; return set{1,2, 5}; end; [1] + foo{}\n",
        "fn foo args; return set{1,2, 5}; end; dict{1,2} + foo{}\n",
        "fn foo args; return [1,2, [5]]; end; set{foo{}} in set{1,2, 5}\n",
        'data Class [rand]; class = Class{set{[1,2, "5"]}}; class.rand in set{1,2, 5}\n',
        "data Class [rand]; class = Class{set{[1,2, 5]}}; class.rand in dict{1,2}\n",
        # illegal built in dict function
        "fn foo args; return [1,2, 5]; end; dict{foo{}}\n",
        "fn foo args; return [[1],2]; end; dict{foo{}}\n",
        "fn foo args; return [set{1},2]; end; dict{foo{}}\n",
        "fn foo args; return [dict{1,2},2]; end; dict{foo{}}\n",
        "dict{1,2} * dict{[1,2]}\n",
        "dict{1,2} / dict{[1,2]}\n",
        "dict{1,2} // dict{[1,2]}\n",
        "dict{1,2} ** dict{[1,2]}\n",
        "dict{1,2} > dict{[1,2]}\n",
        "dict{1,2} >= dict{[1,2]}\n",
        "dict{1,2} < dict{[1,2]}\n",
        "dict{1,2} <= dict{[1,2]}\n",
        "dict{1,2} in dict{[1,2]}\n",
        "fn foo args; return [1,2, 5]; end; data Class [rand]; class = Class{foo{}}; dict{class.rand}\n",
        "fn foo args; return [1,2, 5]; end; data Class [rand]; class = Class{foo{}}; dict{class.rand}\n",
        # illegal built in range function
        "range{9.9}\n",
        "range{1.1, 9}\n",
        "range{1, 9, 2.2}\n",
        "range{[1.1, 9, 2]}\n",
        "range{9, 9, false}\n",
        "range{dict{1,2}}\n",
        "range{set{[1]}}\n",
        "range{[[1]]}\n",
        "data Class [rand]; class = Class{[[1]]}; range{class.rand}\n",
        "data Class [rand]; class = Class{dict{1,2}}; range{class.rand}\n",
        # illegal in operator
        "fn bar args\n return 5\nend\nbar{} in 1\n",
        "fn bar args\n return 5\nend\nbar{} in true\n",
        'fn bar args\n return 5\nend\nbar{} in "5"\n',
        'fn bar args\n return "5"\nend\nbar{} in 5\n',
        'fn bar args\n return "5"\nend\nbar{} in true\n',
        "fn bar args\n return [5]\nend\nbar{} in 5\n",
        "fn bar args\n return [5]\nend\nbar{} in true\n",
        'fn bar args\n return [5]\nend\nbar{} in "5"\n',
        "fn bar args\n return true\nend\nbar{} in 1\n",
        "fn bar args\n return false\nend\nbar{} in true\n",
        'fn bar args\n return true\nend\nbar{} in "5"\n',
        "fn bar args; return false; end; data Class [rand]; class = Class{bar}; class.rand{} in 1\n",
        "fn bar args; return [5]; end; data Class [rand]; class = Class{bar}; class.rand{} in 1\n",
        # illegal multi-variable assignment
        "fn bar args\n return 5\nend\n[hello] = bar{}\n",
        "fn bar args\n return true\nend\n[hello] = bar{}\n",
        'fn bar args\n return "5"\nend\n[hello] = bar{}\n',
        "fn bar args\n return 4\nend\n[hello] = bar{}\n",
        "fn bar args \nend\n hello = [5]\n[hello] = bar{}\n",
        'fn bar args\n return ["5"]\nend\n hello = "5"\n[hello] *= bar{}\n',
        "fn bar args; return [false]; end; data Class [rand]; class = Class{bar}; [class.rand{}[0]] *= [set{1}]\n",
        'fn bar args; return [5]; end; data Class [rand]; class = Class{bar}; [class.rand{}[0]] /= ["1"]\n',
        # invalid dataclass stuff
        # field read on non-instance via dynamic callee → runtime field-access error
        "fn mk args\n return [1]\nend\nx = mk{}; print{x.foo}\n",
        # augmented assign on field whose runtime value defaults to None → op error
        'data P [x]; p = P{}; p.x += "s"\n',
        # field read on non-instance (set) via dynamic path
        "fn mk args\n return set{1}\nend\nx = mk{}; print{x.a}\n",
        # index OOB before field read in a chain → index runtime error
        "data P [x]; arr = [P{1}]; print{arr[1+1].x}\n",
        # calling an instance like a function → not callable
        "data P [x]; fn foo args; return P{1}; end; foo{}{}\n",
    ],
)
def test_evaluator_invalid(program, tmp_path):
    """Each program here is expected to raise *EvaluatorError*."""
    with pytest.raises(EvaluatorError):
        evaluate(program, tmp_path)
