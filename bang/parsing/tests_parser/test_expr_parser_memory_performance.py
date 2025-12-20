from __future__ import annotations

import gc
import tempfile
from pathlib import Path

from guppy import hpy

from bang.lexing.lexer import Lexer
from bang.parsing.expression_parser import ExpressionParser

CODE = "x = 1 + 2 * (3 + 4)\ny = arr[1][2][i + 1]\nz = foo{1,2,3}.bar[baz]\n"


def parse_once(tokens, file_path: str):
    parser = ExpressionParser(tokens, file_path)
    parser.split()
    parser.loading_into_algos()


def run(file_path: str, loops: int = 10, stage_breakdown: bool = True):
    hp = hpy()

    # --- Lex once (excluded from relative heap measurements below) ---
    tokens = list(Lexer(file_path).tokenizer())

    # Clean baseline so the deltas are less noisy
    gc.collect()

    if not stage_breakdown:
        # Measure total net heap growth for parsing loops
        hp.setrelheap()
        for _ in range(loops):
            parse_once(tokens, file_path)

        gc.collect()
        print("\n=== Relative heap growth: PARSE (total) ===")
        print(hp.heap())
        print("\n=== By type (relative) ===")
        print(hp.heap().bytype)
        return

    # --- Stage-by-stage breakdown for ONE loop ---
    # (Stage breakdown is most readable at loops=1; you can still
    # run loops>1 below if you want totals.)
    print("\n=== Stage breakdown (relative deltas) ===")

    gc.collect()
    parser = ExpressionParser(tokens, file_path)

    hp.setrelheap()
    # nothing executed here besides object creation above; show init cost
    gc.collect()
    print("\n[after ExpressionParser(...) init] (relative)")
    print(hp.heap())

    hp.setrelheap()
    parser.split()
    gc.collect()
    print("\n[after parser.split()] (relative)")
    print(hp.heap())

    hp.setrelheap()
    parser.loading_into_algos()
    gc.collect()
    print("\n[after parser.loading_into_algos()] (relative)")
    print(hp.heap())

    # --- Optional: total across multiple loops (net growth) ---
    if loops > 1:
        gc.collect()
        hp.setrelheap()
        for _ in range(loops):
            parse_once(tokens, file_path)
        gc.collect()
        print(f"\n=== Relative heap growth: PARSE (total over {loops} loops) ===")
        h = hp.heap()
        print(h)
        print("\n=== By type (relative) ===")
        print(h.bytype)


def main():
    with tempfile.TemporaryDirectory() as d:
        tmp_path = Path(d)
        file = tmp_path / "code.txt"
        file.write_text(CODE)

        # Try loops=1 first to reduce noise, then increase.
        run(str(file), loops=1, stage_breakdown=True)


if __name__ == "__main__":
    main()
