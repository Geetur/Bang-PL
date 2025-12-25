# bang/cli.py
from __future__ import annotations

import argparse
import inspect
import sys

from .lexing.lexer import Lexer, LexerError
from .parsing.control_flow_parser import ControlFlowParser
from .parsing.expression_parser import ExpressionParser, ParserError
from .runtime.evaluator import Evaluator, EvaluatorError
from .semantic.semantic_analysis import SemanticAnalysis, SemanticError


def run_file(path: str, *, show_tokens=False, show_ast=False, trace=False) -> int:
    try:
        lex = Lexer(path)
        tokens = lex.tokenizer()

        ex = ExpressionParser(tokens, lex.text)
        ex.split()
        if show_tokens:
            print(ex.post_split)
        ex.loading_into_algos()

        cf = ControlFlowParser(lex.text, ex.post_SYA)
        roots = cf.blockenize()
        if show_ast:
            print(roots)

        SemanticAnalysis(lex.text, roots).walk_program()

        # --- only pass trace if supported ---
        kwargs = {}
        params = inspect.signature(Evaluator.__init__).parameters
        if trace and ("trace" not in params):
            print("note: this build doesn't support --trace; running normally.", file=sys.stderr)
        elif "trace" in params:
            kwargs["trace"] = bool(trace)

        Evaluator(lex.text, roots, **kwargs).eval_program()
        return 0
    except LexerError as e:
        print(e, file=sys.stderr)
        return 1
    except ParserError as e:
        print(e, file=sys.stderr)
        return 2
    except SemanticError as e:
        print(e, file=sys.stderr)
        return 3
    except EvaluatorError as e:
        print(e, file=sys.stderr)
        return 4


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="bang", description="Bang language runner")
    p.add_argument("file", help="Path to a .bang file")
    p.add_argument("--tokens", action="store_true", help="Print tokens before running")
    p.add_argument("--ast", action="store_true", help="Print parsed block AST before running")
    p.add_argument("--trace", action="store_true", help="Trace evaluation (if supported)")
    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    code = run_file(args.file, show_tokens=args.tokens, show_ast=args.ast, trace=args.trace)
    sys.exit(code)
