from __future__ import annotations

import tempfile
from pathlib import Path

from line_profiler import LineProfiler

from bang.lexing.lexer import Lexer

CODE = "x = 1 + 2 * (3 + 4)\n"

#y = arr[1][2][i + 1]\nz = foo{1,2,3}.bar[baz]\n"


def run(file_path: str, loops: int = 1000):
    for _ in range(loops):
        tokens = Lexer(file_path).tokenizer()


def main():
    with tempfile.TemporaryDirectory() as d:
        tmp_path = Path(d)
        file = tmp_path / "code.txt"
        file.write_text(CODE)

        lp = LineProfiler()

        # Add the exact hot methods you care about:
        lp.add_function(Lexer.tokenizer)

        lp_wrapper = lp(lambda: run(str(file)))
        lp_wrapper()
        lp.print_stats(output_unit=1e-6)  # microseconds


if __name__ == "__main__":
    main()