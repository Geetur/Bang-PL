import pytest

from bang.lexing.lexer import Lexer
from bang.parsing.expression_parser import ExpressionParser
from bang.parsing.control_flow_parser import ControlFlowParser
from bang.semantic.semantic_analysis import SemanticAnalysis
from bang.runtime.evaluator import Evaluator, EvaluatorError


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

        #array arithmetic
        "x = [1]\ny = [2]\nz = x + y\n",
        "x = [1,2]\ny = [2]\nz = x - y\n",
        'x = [1]\ny = 2\nz = x * y\n',
        'x = [1]\ny = [2]\nz = x * y\n',
        'x = [1,2,3]\ny = [2]\nz = x / y\n',
        "x = 2\ny = [1]\nz = x * y\n",

        "x = [1]\ny = [2]\nx += y\n",
        "x = [1,2]\ny = [2]\nx -= y\n",
        'x = [1]\ny = 2\nx *= y\n',
        'x = [1]\ny = [2]\nx *= y\n',
        'x = [1,2,3]\ny = [2]\nx /= y\n',
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
        'dict{1,2}[1]\n',

        # Function definition & call
        "fn add args\n return args[0] + args[1]\nend\nresult = add{2,3}\n",

        # Boolean logic evaluated at run‑time
        "flag = true\nother = false\nres = flag && !other\n",

        #built in sum function
        'sum{[1,2,3,4]}\n',
        'sum{[1,2,false,true]}\n'
        'sum{[[1],[2],[3],[4]]}\n',
        'sum{[1,2,3,4]}\n',
        'sum{["1","2","3","4"]}\n',
        'sum{["12","3","4"]}\n',
        'print{sum{[dict{1, 2}, dict{2, 3}, dict{4, 5}]}}\n',
        'print{sum{[set{[1, 2]}, set{[2, 3]}, set{[4, 5]}]}}\n',

        #built in min function
        'min{[1,2,3,4]}\n',
        'min{[1,2,false,true]}\n'
        'min{[[1],[2],[3],[4]]}\n',
        'min{[1,2,3,4]}\n',
        'min{["1","2","3","4"]}\n',
        'min{["1","2","3","4"]}\n',

        #built in max function
        'max{[1,2,3,4]}\n',
        'max{[1,2,false,true]}\n'
        'max{[[1],[2],[3],[4]]}\n',
        'max{[1,2,3,4]}\n',
        'max{["1","2","3","4"]}\n',
        'max{["1","2","3","4"]}\n',

        #built in len function
        'len{[1,2,3,4,5]}\n',
        'len{[1,2,3,4,"5"]}\n',
        'len{[1,2,3,4,[5]]}\n',
        'len{"12fgdgd"}\n',

        #built in print function
        'print{[1,2,3,4,5]}\n',
        'print{1,2,3,4,5}\n',
        'print{[1,2,3,4,5], 1}\n',
        'print{[1,2,3,4,5], "1"}\n',
        'print{"ffsfsfsfs"}\n',
        'print{true, false}\n',
        'print{"ffsfsfsfs"}\n',
        'x = "12"\ny = 2\nz = true\n print{x,y,z}\n',
        'x = [[0] * 5] * 5\nprint{x}\n',
        'print{["sfdsdffsfsd", 1, false, true, ["hello"]]}\n',
        'print{set{[1,2,3]}}\n',
        'print{dict{1,2}}\n',
        'print{dict{[[1,2], [2,3], [4,5]]}}\n',


        #built in sort function
        'sort{[1,2, 3]}\n',
        'sort{[1,2, 3]}\n',
        'sort{[[1,2, 3], [1,2,4]]}\n',
        'sort{["1","2", "3"]}\n',
        'sort{["323425232353456"]}\n',
        'sort{[1,true, false]}\n',
        

        # built in set function

        'set{[1,2, "5"]}\n',
        'set{[1,2, 4]}\n',
        'set{[1,2, true]}\n',
        'set{[1,2, false]}\n',
        'set{}\n',

        'a= set{[1,2, 4]} + set{[1,6,7]}\n',
        'a= set{} + set{[1,6,7]}\n',
        'a= set{[1,2, 4]} - set{[1,6,7]}\n',
        'a= set{[1,2, 4]} - set{}\n',

        'a= set{[1,2, 4]} > set{[1,6,7]}\n',
        'a= set{} >= set{[1,6,7]}\n',
        'a= set{[1,2, 4]} < set{[1,6,7]}\n',
        'a= set{[1,2, 4]} <= set{}\n',

        'a= set{[1,2, 4]} == set{[1,6,7]}\n',
        'a= set{} != set{[1,6,7]}\n',
        'a= set{[1,2, 4]} && set{[1,6,7]}\n',
        'a= set{[1,2, 4]} || set{}\n',

        #built in dict function
        'dict{1,2}\n',
        'dict{1,false}\n',
        'dict{1,"2"}\n',
        'dict{1,[3]}\n',
        'dict{1,set{[1]}}\n',
        'dict{1,dict{1, 2}}\n',

        'dict{[[1,dict{1, 2}], [1, 2], [2, set{[1]}], [9, false], [10, "hi"]]}\n',
        
        'dict{}\n',

        'dict{1,2} + dict{3,2}\n',
        'dict{1,2} + dict{1,2}\n',
        'dict{1,2} + dict{}\n',

        'dict{1,2} - dict{3,2}\n',
        'dict{1,2} - dict{1,2}\n',
        'dict{1,2} - dict{}\n',

        'dict{1,2} == dict{3,2}\n',
        'dict{1,2} != dict{1,2}\n',
        'dict{1,2} && dict{}\n',

        'dict{1,2} || dict{3,2}\n',


        # in operator
        "fn bar args\n return 5\nend\nbar{} in [1]\n",
        
        'fn bar args\n return "5"\nend\nbar{} in "5"\n',
        'fn bar args\n return "5"\nend\nbar{} in [true]\n',
        
        'fn bar args\n return [5]\nend\nbar{} in [5]\n',

        "fn bar args\n return true\nend\nbar{} in [1]\n",

        # multivariable assignment

        'fn bar args\n return [5]\nend\n[hello] = bar{}\n',
        'fn bar args\n return [true]\nend\n[hello] = bar{}\n',
        'fn bar args\n return ["5"]\nend\n[hello] = bar{}\n',
        'fn bar args\n return [[4]]\nend\n[hello] = bar{}\n',

        'fn bar args\n return ["5", "4"]\nend\n[hello, dict{5, "place_holder"}[5]] = bar{}\n',
        'fn bar args\n return [[4], [1, 2]]\nend\n[hello, [x, y]] = bar{}\n',
        'fn bar args\n return ["5", "4"]\nend\n[hello, [1, 2][1]] = bar{}\n',

        'fn bar args\n return [5]\nend\n hello = 5\n [hello] += bar{}\n',
        'fn bar args\n return [true]\nend\n hello = 5\n[hello] += bar{}\n',
        'fn bar args\n return ["5"]\nend\n hello = "5"\n[hello] += bar{}\n',
        'fn bar args\n return [[4]]\nend\n hello = [5]\n[hello] += bar{}\n',

        'fn bar args\n return [5]\nend\n hello = 5\n [hello] -= bar{}\n',
        'fn bar args\n return [true]\nend\n hello = 5\n[hello] -= bar{}\n',
        'fn bar args\n return ["5"]\nend\n hello = "5"\n[hello] -= bar{}\n',
        'fn bar args\n return [[4]]\nend\n hello = [5]\n[hello] -= bar{}\n',

        'fn bar args\n return [5]\nend\n hello = 5\n [hello] *= bar{}\n',
        'fn bar args\n return [true]\nend\n hello = 5\n[hello] *= bar{}\n',
        'fn bar args\n return [5]\nend\n hello = "5"\n[hello] *= bar{}\n',
        'fn bar args\n return [[4]]\nend\n hello = [5]\n[hello] *= bar{}\n',
        'fn bar args\n return [4]\nend\n hello = [5]\n[hello] *= bar{}\n',

        'fn bar args\n return [5]\nend\n hello = 5\n [hello] /= bar{}\n',
        'fn bar args\n return [true]\nend\n hello = 5\n[hello] /= bar{}\n',
        'fn bar args\n return ["5"]\nend\n hello = "5"\n[hello] /= bar{}\n',
        'fn bar args\n return [[4]]\nend\n hello = [5]\n[hello] /= bar{}\n',

        # weird function calls
        "fn foo args\n return dict\nend\nx = foo{}{1,2}\n",
        "fn foo args\n return dict\nend\nx = foo{}{[[1,2], [3,4], [5, 6]]}\n",

        "fn foo args\n return set\nend\nx = foo{}{[1,2]}\n",

        'fn foo args\n return len\nend\nx = foo{}{"123456hi"}\n',

        'fn foo args\n return [len]\nend\nx = foo{}[0]{"123456hi"}\n',
        'fn foo args\n return [[[len]]]\nend\nx = foo{}[0][0][0]{"123456hi"}\n',


        
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

        # Index out of bounds that was not detectable statically
        "arr = [1]\nidx = 3\nval = arr[idx+5]\n",

        # illegal indexing
        "a = [5]\n b = a[0+1]",
        "a = [5, [2]]\n b = a[0+1][3]",
        "fn bar args\n return [1]\nend\nx = [2,3,4][bar{}]\n",
        'fn bar args\n return "5"\nend\nx = [2,3,4][bar{}]\n',
        'a = dict{1,2}\n b = a[0]\n',
        'a = set{1,2}\n b = a[1]\n',


        #illegal arithmetic
        "fn bar args\n return 5\nend\nx = bar{} + [2,3,4]\n",
        'fn bar args\n return 5\nend\nx = bar{} + "3"\n',
        'fn bar args\n return "5"\nend\nx = 1 + bar{}\n',
        'fn bar args\n return [1]\nend\nx = "1" + bar{}\n',
        'fn bar args\n return "5"\nend\nx = set{1} + bar{}\n',
        'fn bar args\n return [1]\nend\nx = dict{1,2} + bar{}\n',

        #built in sum function
        'sum{[1,2,3,"4"]}\n',
        'sum{1,2,3,4}\n',
        "sum{}\n",

        #built in min function
        'min{[1,2,3,"4"]}\n',
        'min{1,2,3,4}\n',
        "min{}\n",

        #built in max function
        'max{[1,2,3,"4"]}\n',
        'max{1,2,3,4}\n',
        "max{}\n",

        #built in len function
        'len{1}\n',
        "len{}\n",

        #built in sort function
        'sort{[1,2, "5"]}\n',
        'sort{[1,2, [5]]}\n',
        'sort{1,2,5}\n',
        'sort{}\n',

        #built in set function
        'set{[1,2, [5]]}\n',
        'set{[1,2, set{1,2}]}\n',
        'set{[1,2, dict{1,2}]}\n',

        'set{[1,2, 5]} * set{[1,2, 5]}\n',
        'set{[1,2, 5]} / set{[1,2, 5]}\n',
        'set{[1,2, 5]} // set{[1,2, 5]}\n',
        'set{[1,2, 5]} ** set{[1,2, 5]}\n',
        '1 + set{[1,2, 5]}\n',
        'false + set{[1,2, 5]}\n',
        '"1" + set{[1,2, 5]}\n',
        '[1] + set{[1,2, 5]}\n',
        'dict{1,2} + set{[1,2, 5]}\n',
        'set{[1,2, 5]} in set{[1,2, 5]}\n',

        #built in dict function
        'dict{1,2, 5}\n',
        'dict{[1],2}\n',
        'dict{set{1},2}\n',
        'dict{dict{1,2},2}\n',
        'dict{[1,2]}\n',
        

        'dict{1,2} * dict{1,2}\n',
        'dict{1,2} / dict{1,2}\n',
        'dict{1,2} // dict{1,2}\n',
        'dict{1,2} ** dict{1,2}\n',
        'dict{1,2} > dict{1,2}\n',
        'dict{1,2} >= dict{1,2}\n',
        'dict{1,2} < dict{1,2}\n',
        'dict{1,2} <= dict{1,2}\n',
        'dict{1,2} in dict{1,2}\n',

        # illegal in operator
        "fn bar args\n return 5\nend\nbar{} in 1\n",
        "fn bar args\n return 5\nend\nbar{} in true\n",
        'fn bar args\n return 5\nend\nbar{} in "5"\n',
        
        'fn bar args\n return "5"\nend\nbar{} in 5\n',
        'fn bar args\n return "5"\nend\nbar{} in true\n',
        
        'fn bar args\n return [5]\nend\nbar{} in 5\n',
        'fn bar args\n return [5]\nend\nbar{} in true\n',
        'fn bar args\n return [5]\nend\nbar{} in "5"\n',

        "fn bar args\n return true\nend\nbar{} in 1\n",
        "fn bar args\n return false\nend\nbar{} in true\n",
        'fn bar args\n return true\nend\nbar{} in "5"\n',

        # illegal multi-variable assignment
        
        'fn bar args\n return 5\nend\n[hello] = bar{}\n',
        'fn bar args\n return true\nend\n[hello] = bar{}\n',
        'fn bar args\n return "5"\nend\n[hello] = bar{}\n',
        'fn bar args\n return 4\nend\n[hello] = bar{}\n',

        'fn bar args \nend\n hello = [5]\n[hello] = bar{}\n',

        'fn bar args\n return ["5"]\nend\n hello = "5"\n[hello] *= bar{}\n',

    ],
)
def test_evaluator_invalid(program, tmp_path):
    """Each program here is expected to raise *EvaluatorError*."""
    with pytest.raises(EvaluatorError):
        evaluate(program, tmp_path)