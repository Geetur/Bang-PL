from __future__ import annotations

import tempfile
from pathlib import Path

from line_profiler import LineProfiler

from bang.lexing.lexer import Lexer
from bang.parsing.expression_parser import ExpressionParser

CODE = "x = 1 + 2 * (3 + 4)\ny = arr[1][2][i + 1]\nz = foo{1,2,3}.bar[baz]\n"


def run(file_path: str, loops: int = 1):
    # parser-only: lex once
    tokens = Lexer(file_path).tokenizer()
    for _ in range(loops):
        parser = ExpressionParser(tokens, file_path)
        parser.split()
        parser.loading_into_algos()


def main():
    with tempfile.TemporaryDirectory() as d:
        tmp_path = Path(d)
        file = tmp_path / "code.txt"
        file.write_text(CODE)

        lp = LineProfiler()

        # Add the exact hot methods you care about:
        lp.add_function(ExpressionParser.loading_into_algos)
        lp.add_function(ExpressionParser.shunting_yard_algo)
        lp.add_function(ExpressionParser.handle_array_literals)
        lp.add_function(ExpressionParser.handle_function_call)
        lp.add_function(ExpressionParser.handle_index)

        lp_wrapper = lp(lambda: run(str(file)))
        lp_wrapper()
        lp.print_stats(output_unit=1)  # microseconds


if __name__ == "__main__":
    main()
