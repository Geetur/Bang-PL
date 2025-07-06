import pytest

from lexer import Lexer
from expression_parser import ExpressionParser
from control_flow_parser import ControlFlowParser
from semantic_analysis import SemanticAnalysis
from evaluator import Evaluator, EvaluatorError


def evaluate(code: str, tmp_path):
    """Tokenises, parses, semantically analyses **and** executes a small Bang
    program.  Any *EvaluatorError* raised at run‑time will bubble up to the test
    layer just like *SemanticError* does in the compile‑time suite.
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

        'x = "12"\ny = "2"\nz = x - y\n',
        'x = "1,2"\ny = ","\nz = x / y\n',
        'x = "1"\ny = 2\nz = x * y\n',

        # Array indexing with run‑time index
        "arr = [10, 20, 30]\nidx = 1\nval = arr[idx]\n",

        # Function definition & call
        "fn add args\n return args[0] + args[1]\nend\nresult = add{2,3}\n",

        # Boolean logic evaluated at run‑time
        "flag = true\nother = false\nres = flag && !other\n",
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

        #illegal arithmetic
        "fn bar args\n return 5\nend\nx = bar{} + [2,3,4]\n",
        'fn bar args\n return 5\nend\nx = bar{} + "3"\n',
        'fn bar args\n return "5"\nend\nx = 1 + bar{}\n',
        'fn bar args\n return [1]\nend\nx = "1" + bar{}\n',


    ],
)
def test_evaluator_invalid(program, tmp_path):
    """Each program here is expected to raise *EvaluatorError*."""
    with pytest.raises(EvaluatorError):
        evaluate(program, tmp_path)