import pytest
from bang.lexing.lexer import Lexer
from bang.parsing.expression_parser import ExpressionParser
from bang.parsing.control_flow_parser import ControlFlowParser
from bang.semantic.semantic_analysis import SemanticAnalysis, SemanticError


def analyze(code: str, tmp_path):
    """Tokenises, parses and semantically analyses a small Bang program.
    Any SemanticError raised by the analyser will bubble up to the test layer.
    """
    src = tmp_path / "temp.bang"
    src.write_text(code)

    # Lexing
    lexer = Lexer(str(src))
    tokens = lexer.tokenizer()

    # Expression‑level parsing → list of nodes
    e_parser = ExpressionParser(tokens, lexer.file)
    e_parser.split()
    e_parser.loading_into_algos()

    # Control‑flow grouping → roots
    cf_parser = ControlFlowParser(lexer.file, e_parser.post_SYA)
    roots = cf_parser.blockenize()

    # Semantic analysis (the unit under test)
    sema = SemanticAnalysis(lexer.file, roots)
    sema.walk_program()
    return sema  # returned so tests can make deeper assertions later if desired


# ----------------------------
# Positive test‑cases (should *not* raise)
# ----------------------------
@pytest.mark.parametrize(
    "program",
    [
        # Simple arithmetic with numbers
        "x = 1\ny = 2\nz = x + y\n",
        "x = 1.1\ny = 2\nz = x + y\n",
        "x = -1.1\ny = 2\nz = x + y\n",
        "x = -1.1\ny = 2\nz = x - y\n",
        "x = -1.1\ny = 2\nz = x / y\n",
        "x = -1.1\ny = 2\nz = x * y\n",
        "x = -1.1\ny = 2\nz = x // y\n",
        "x = -1.1\ny = 2\nz = x ** y\n",

        "x = 1\ny = 2\nx += y\n",
        "x = 1.1\ny = 2\nx += y\n",
        "x = -1.1\ny = 2\nx += y\n",
        "x = -1.1\ny = 2\nx -= y\n",
        "x = -1.1\ny = 2\nx /= y\n",
        "x = -1.1\ny = 2\nx *= y\n",
        

        # Mixing numbers and booleans in arithmetic (permitted by Bang semantics)
        "x = 1\ny = true\nz = x + y\n",
        "x = 1\ny = false\nz = x + y\n",
        "x = 1\ny = !true\nz = x + y\n",
        "x = 1\ny = true\nz = x - y\n",
        "x = 1\ny = false\nz = x * y\n",
        "x = 1\ny = !true\nz = x / y\n",
        "x = 1\ny = true\nz = x ** y\n",
        "x = 1\ny = false\nz = x // y\n",


         "x = 1\ny = true\nx += y\n",
        "x = 1\ny = false\nx += y\n",
        "x = 1\ny = !true\nx += y\n",
        "x = 1\ny = true\nx -= y\n",
        "x = 1\ny = false\nx *= y\n",
        "x = 1\ny = !true\nx /= y\n",

        # String concatenation of matching types
        'a = \"hello\"\nb = \"world\"\nc = a + b\n',
        'a = \"hello\"\nb = \"world\"\nc = a - b\n',
        'a = \"hello\"\nb = \"world\"\nc = a * b\n',
        'a = \"hello\"\nb = \"world\"\nc = a / b\n',
        'a = \"hello\"\nb = \"world\"\nc = a // b\n',
        'a = \"hello\"\nb = \"world\"\nc = a ** b\n',

        'a = \"hello\"\nb = \"world\"\na += b\n',
        'a = \"hello\"\nb = \"world\"\na -= b\n',
        'a = \"hello\"\nb = \"world\"\na *= b\n',
        'a = \"hello\"\nb = \"world\"\na /= b\n',


        # Unary on a number
        "x = -5\n",
        "x = +5\n",
        "x = -+5\n",
        "x = -+-5\n",
        "x = +++-5\n",
        "x = ---+5\n",

        # Basic array indexing
        "arr = [1,2,3]\nx = arr[1]\n",
        "arr = [1,2,3]\nx = arr[0]\n",
        "arr = [1,2,3]\nx = arr[2]\n",

        # Nested array indexing
        "arr = [[1,2],[3,4]]\nx = arr[0][0]\n",
        "arr = [[1,2],[3,4]]\nx = arr[1][0]\n",
        "arr = [[1,2],[3,4]]\nx = arr[0][1]\n",
        "arr = [[1,2],[3,4]]\nx = arr[1][1]\n",

        # Control‑flow with break / continue inside a loop
        "for i 5\n    if true\n        break\n    end\n    continue\nend\n",

        'for i "5"\n x=1\n end',


        # if / else branches
        "if true\n    x = 1\nelse\n    x = 2\nend\nend\n",

        # Valid compound assignment (variable previously initialised)
        "x = 1\nx += 3\n",
        "x = 1\nx -= -3\n",
        "x = 1\nx *= 3.3\n",
        "x = 1\nx /= -+3.3\n",

        'a = \"hello\"\nb = \"world\"\na += b\n',
        'a = \"hello\"\nb = \"world\"\na -= b\n',
        'a = \"hello\"\nb = \"world\"\na *= b\n',
        'a = \"hello\"\nb = \"world\"\na /= b\n',

        "x = 1\ny = true\n x += y\n",
        "x = 1\ny = false\n x -= y\n",
        "x = 1\ny = !true\nx *= y\n",
        "x = 1\ny = true\nx /= y\n",

        "x = [1]\ny = [2]\n x += y\n",
        "x = [1]\ny = [2]\n x -= y\n",
        "x = [1]\ny = [2]\nx *= y\n",
        "x = [1]\ny = [2]\nx /= y\n",

        'a = [1]\nb = [2]\n a[0] += b[0]\n',
        'a = [1]\nb = [true]\n a[0] -= b[0]\n',
        'a = [1]\nb = [false]\n a[0] *= b[0]\n',
        'a = [1]\nb = [2.2]\n a[0] /= b[0]\n',

        'a = ["1"]\nb = ["2"]\n a[0] += b[0]\n',
        'a = ["1"]\nb = ["true"]\n a[0] -= b[0]\n',
        'a = ["1"]\nb = ["false"]\n a[0] *= b[0]\n',
        'a = ["1"]\nb = ["2"]\n a[0] /= b[0]\n',

        "x = !5\n",
        'x = !"1"\n',
        "x = ![1]\n x = !x[0]",
        "x = [1]\n x = 2\n x && y",
        "x = true\n x = false\n x || y",
        'x = [true]\n x = "shello"\n x || y',
        'x = 1\n x = "shello"\n x >= y',
        'x = [1]\n x = "shello"\n x <= y',
        'x = [1]\n x = "shello"\n x == y',
        'x = 1\n x = "shello"\n x != y',
        'x = 1\n x = "shello"\n x && y',
        'x = 1\n x = "shello"\n x || y',


        # expressions with functions (first class)

        "fn foo args\n return [1,2,3]\nend\nfor i foo{}\n x = i\nend\n",

        # Function result used in arithmetic
        "fn bar args\n return 5\nend\nx = bar{} + 3\n",

        # Function result used in indexing
        "fn get_arr args\n return [10, 20, 30]\nend\nx = get_arr{}[1]\n",

        # Function result used in nested indexing
        "fn foo args\n return [5,6,7]\nend\nx = foo{}[0]\n",

        # Function result used as index
        "fn indexer args\n return 1\nend\narr = [10, 20, 30]\nx = arr[indexer{}]\n",

        # in operator
        'a=[5] in [5, 4, 3]\n',
        'a=[5] in [1]\n',
        'a=5 in [5]\n',
        'a="5" in [5]\n',
        'a=true in [5]\n',
        'a=false in [5]\n',
        
        'a="5" in "543534"\n',
        'a="5" in ""\n',



        # there are many examples that pass the semantic analyzer but
        # would throw a runetime error because in this semantic analyzer we are simply
        # performing static analysis; anything that would require evaluation
        # is not checked here: for example a = [5]\n b = a[0+1] would not throw an error
        # because 0 + 1 requires evaluation to be known as 1. we can optimize this with constant folding in
        # the parsing stage but that is not necessary currently, although would be great later.
        # constant folding is just saying, "is this bin op node two literals?" if so, we can
        # evaluate them here and just merge the bin op node into a literal
        "a = [5]\n b = a[0+1]",
        "a = [5, [2]]\n b = a[0+1][3]",
        "fn bar args\n return 5\nend\nx = bar{} + [2,3,4]\n",
        "fn bar args\n return 5\nend\nx = bar{} + true\n",
        "fn bar args\n return 5\nend\nx = bar{} + false\n",
        'fn bar args\n return 5\nend\nx = bar{} + "3"\n',


    ],
)
def test_semantic_valid(program, tmp_path):
    """The following programs are *semantically valid* and should analyse without error."""
    analyze(program, tmp_path)  # will raise on failure


# ----------------------------
# Negative test‑cases (should raise SemanticError)
# ----------------------------
@pytest.mark.parametrize(
    "program",
    [
        # Heterogeneous arithmetic (number + string)
        'x = 1\ny = \"str\"\nz = x + y\n',

        # Use of undeclared identifier
        "x = y\n",

        # break outside any loop
        "break\n",

        # continue outside any loop
        "continue\n",

        # Indexing a non‑array value
        "x = 5\ny = x[0]\n",

        # Index out of bounds where the index is a compile‑time constant
        "arr = [1]\nx = arr[2]\n",

        # Invalid compound assignment (string += number)
        'x = \"hello\"\nx += 1\n',

        # Compound assignment to an undeclared variable
        "x += 1\n",

        # Loop variable escaping its scope
        "for i 5\n    x = i\nend\ny = i\n",

        # Unary minus applied to a string (invalid operand type)
        'x = -\"hello\"\n',


        
        # the current grammar says we can only
        # perform arithmetic operations on
        # (numbers && bools) or (same types)
        # this could change i think a really cool overload
        # is when you do arr - 1 to pop an item of an arr
        'a = ["1"]\nb = [2]\n a[0] += b[0]\n',
        'a = ["1"]\nb = [true]\n a[0] -= b[0]\n',


        'a = [1]\nb = ["2"]\n a[0] /= b[0]\n',

        'a = ["1"]\nb = [[1]]\n a[0] += b[0]\n',
        'a = [1]\nb = [[true]]\n a[0] -= b[0]\n',


        "x = 5\n p= 1 + x{1}",

        'a = [5, [2]]\n b = a["B" + "a"][3]',
        'a = [5, [2]]\n b = a[[1] + [1]][3]',
        'a = [5, [2]]\n b = a[[1] + "a"][3]',
        'a = [5, [2]]\n b = a[1 + "a"][3]',
        'a = [5, [2]]\n b = a[1 + [1]][3]',

        #in operator
        'a = [5] in 5\n',
        'a = 5 in 5\n',
        'a=true in 5\n'
        'a=false in 5\n',
        'a="5" in 5\n',

        'a=5 in true\n',
        'a=5 in false\n'
        'a=[1] in true\n',
        'a=[1] in false\n',
        'a=true in true\n',
        'a=false in false\n'
        'a="hello" in true\n',
        'a="hello" in false\n',

        'a=5 in "hello"\n',
        'a=[1] in "hello"\n',
        'a=true in "hello"\n',


    ],
)
def test_semantic_invalid(program, tmp_path):
    """Each program here should raise a *SemanticError*."""
    with pytest.raises(SemanticError):
        analyze(program, tmp_path)
