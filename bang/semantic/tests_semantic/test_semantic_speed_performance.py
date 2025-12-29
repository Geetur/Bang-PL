from __future__ import annotations

import tempfile
from pathlib import Path

from line_profiler import LineProfiler

from bang.lexing.lexer import Lexer
from bang.parsing.expression_parser import ExpressionParser
from bang.parsing.control_flow_parser import ControlFlowParser
from bang.semantic.semantic_analysis import SemanticAnalysis

# A representative chunk of code that exercises:
# 1. Variable initialization & lookups (heavy map usage)
# 2. Function definitions & scopes (scope stack operations)
# 3. Control flow (if/else/loops)
# 4. Expressions & Assignments
CODE = """
a = 1; b = 2; s = "5"; s += "fsdf"
"""

def run(file_path: str, loops: int = 1000):
    # 1. Lexing
    tokens = Lexer(file_path).tokenizer()

    # 2. Expression Parsing
    expr_parser = ExpressionParser(tokens, file_path)
    expr_parser.split()
    expression_nodes = expr_parser.loading_into_algos()

    # 3. Control Flow Parsing (AST Generation)
    # We do this OUTSIDE the loop because we only want to profile the Semantic Analysis
    cf_parser = ControlFlowParser(file_path, expression_nodes)
    roots = cf_parser.blockenize()

    # 4. Profile Loop
    for _ in range(loops):
        # We re-instantiate to ensure a fresh scope_stack for every run
        analyzer = SemanticAnalysis(file_path, roots)
        analyzer.walk_program()


def main():
    with tempfile.TemporaryDirectory() as d:
        tmp_path = Path(d)
        file = tmp_path / "code.txt"
        file.write_text(CODE)

        lp = LineProfiler()

        # Add the hot methods for Semantic Analysis
        lp.add_function(SemanticAnalysis.walk_program)
        lp.add_function(SemanticAnalysis.walk_construct)
        lp.add_function(SemanticAnalysis.walk_assignments)
        lp.add_function(SemanticAnalysis.walk_expression)
        
        # These are likely bottlenecks due to repeated dictionary lookups
        lp.add_function(SemanticAnalysis.search_for_var)
        lp.add_function(SemanticAnalysis.initalize_var)

        lp_wrapper = lp(lambda: run(str(file)))
        lp_wrapper()
        lp.print_stats(output_unit=1e-6)  # microseconds


if __name__ == "__main__":
    main()