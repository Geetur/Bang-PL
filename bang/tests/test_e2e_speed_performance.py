# bench_bang_e2e.py
from __future__ import annotations

import argparse
import gc
import os
import statistics as stats
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Tuple


LINE = "x = 1 + 2 * (3 + 4)\n"


# ----------------------------
# Program generation
# ----------------------------
def write_program(tmpdir: Path, n_lines: int) -> Path:
    path = tmpdir / "bench.bang"
    path.write_text(LINE * n_lines, encoding="utf-8")
    return path


# ----------------------------
# Stats helpers
# ----------------------------
def summarize(times: List[float]) -> Tuple[float, float, float, float]:
    ts = sorted(times)
    med = stats.median(ts)
    mn = ts[0]
    mx = ts[-1]
    p95 = ts[int(0.95 * (len(ts) - 1))]
    return mn, med, p95, mx


def fmt_seconds(s: float) -> str:
    if s < 1e-6:
        return f"{s*1e9:.1f} ns"
    if s < 1e-3:
        return f"{s*1e6:.2f} µs"
    if s < 1.0:
        return f"{s*1e3:.3f} ms"
    return f"{s:.3f} s"


def fmt_pct(x: float) -> str:
    return f"{x*100:5.1f}%"


# ----------------------------
# In-proc timed pipeline
# ----------------------------
def timed_pipeline_inproc(bang_file: Path) -> Tuple[int, Dict[str, float]]:
    """
    Times the same end-to-end pipeline as bang.cli.run_file(), but returns per-phase timings.
    Phases:
      lex, expr_split, expr_load, cf, sem, eval, total
    """
    from bang.lexing.lexer import Lexer, LexerError
    from bang.parsing.expression_parser import ExpressionParser, ParserError
    from bang.parsing.control_flow_parser import ControlFlowParser
    from bang.semantic.semantic_analysis import SemanticAnalysis, SemanticError
    from bang.runtime.evaluator import Evaluator, EvaluatorError

    t = {}

    try:
        t0 = time.perf_counter()

        # lex
        a0 = time.perf_counter()
        lex = Lexer(str(bang_file))
        tokens = lex.tokenizer()
        a1 = time.perf_counter()
        t["lex"] = a1 - a0

        # expression parsing: split + loading_into_algos
        b0 = time.perf_counter()
        ex = ExpressionParser(tokens, lex.text)
        ex.split()
        b1 = time.perf_counter()
        t["expr_split"] = b1 - b0

        c0 = time.perf_counter()
        ex.loading_into_algos()
        c1 = time.perf_counter()
        t["expr_load"] = c1 - c0

        # control flow parser
        d0 = time.perf_counter()
        cf = ControlFlowParser(lex.text, ex.post_SYA)
        roots = cf.blockenize()
        d1 = time.perf_counter()
        t["cf"] = d1 - d0

        # semantic analysis
        e0 = time.perf_counter()
        SemanticAnalysis(lex.text, roots).walk_program()
        e1 = time.perf_counter()
        t["sem"] = e1 - e0

        # evaluation
        f0 = time.perf_counter()
        Evaluator(lex.text, roots).eval_program()
        f1 = time.perf_counter()
        t["eval"] = f1 - f0

        t1 = time.perf_counter()
        t["total"] = t1 - t0

        return 0, t

    except (LexerError, ParserError, SemanticError, EvaluatorError):
        return 1, t


def measure_inproc(bang_file: Path, iters: int, warmup: int) -> Dict[str, List[float]]:
    # warmup
    for _ in range(warmup):
        rc, _ = timed_pipeline_inproc(bang_file)
        if rc != 0:
            raise RuntimeError(f"warmup failed for {bang_file} (rc={rc})")

    gc.disable()
    series: Dict[str, List[float]] = {k: [] for k in ("lex", "expr_split", "expr_load", "cf", "sem", "eval", "total")}
    try:
        for _ in range(iters):
            rc, t = timed_pipeline_inproc(bang_file)
            if rc != 0:
                raise RuntimeError(f"run failed for {bang_file} (rc={rc})")
            for k in series.keys():
                series[k].append(t.get(k, 0.0))
    finally:
        gc.enable()
    return series


# ----------------------------
# Subprocess mode (total only)
# ----------------------------
def measure_subproc_total_only(bang_file: Path, iters: int, warmup: int, module: str) -> List[float]:
    cmd = [sys.executable, "-m", module, str(bang_file)]

    for _ in range(warmup):
        r = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if r.returncode != 0:
            raise RuntimeError(f"subprocess warmup failed: {r.returncode}")

    times = []
    for _ in range(iters):
        t0 = time.perf_counter()
        r = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        t1 = time.perf_counter()
        if r.returncode != 0:
            raise RuntimeError(f"subprocess run failed: {r.returncode}")
        times.append(t1 - t0)
    return times


# ----------------------------
# Printing
# ----------------------------
def print_total_table(rows):
    header = (
        f"{'lines':>10}  {'min':>12}  {'median':>12}  {'p95':>12}  {'max':>12}  "
        f"{'per-line (median)':>18}  {'lines/sec (median)':>18}"
    )
    print(header)
    print("-" * len(header))
    for r in rows:
        print(
            f"{r['lines']:>10}  {fmt_seconds(r['total_min']):>12}  {fmt_seconds(r['total_med']):>12}  "
            f"{fmt_seconds(r['total_p95']):>12}  {fmt_seconds(r['total_max']):>12}  "
            f"{fmt_seconds(r['per_line_med']):>18}  {r['lines_per_sec_med']:>18,.0f}"
        )


def print_phase_table(rows):
    print("\nPer-phase breakdown (median time per run, plus % of total median):\n")
    header = (
        f"{'lines':>10}  "
        f"{'lex':>12} {'%':>6}  "
        f"{'split':>12} {'%':>6}  "
        f"{'load':>12} {'%':>6}  "
        f"{'cf':>12} {'%':>6}  "
        f"{'sem':>12} {'%':>6}  "
        f"{'eval':>12} {'%':>6}  "
        f"{'total':>12}"
    )
    print(header)
    print("-" * len(header))

    for r in rows:
        total = r["total_med"] if r["total_med"] > 0 else 1e-12

        def cell(name: str) -> Tuple[str, str]:
            v = r[f"{name}_med"]
            return fmt_seconds(v), fmt_pct(v / total)

        lex_s, lex_p = cell("lex")
        split_s, split_p = cell("expr_split")
        load_s, load_p = cell("expr_load")
        cf_s, cf_p = cell("cf")
        sem_s, sem_p = cell("sem")
        eval_s, eval_p = cell("eval")

        print(
            f"{r['lines']:>10}  "
            f"{lex_s:>12} {lex_p:>6}  "
            f"{split_s:>12} {split_p:>6}  "
            f"{load_s:>12} {load_p:>6}  "
            f"{cf_s:>12} {cf_p:>6}  "
            f"{sem_s:>12} {sem_p:>6}  "
            f"{eval_s:>12} {eval_p:>6}  "
            f"{fmt_seconds(r['total_med']):>12}"
        )


def main():
    ap = argparse.ArgumentParser(description="Bang end-to-end benchmark (full pipeline + phase breakdown).")
    ap.add_argument("--mode", choices=("inproc", "subproc"), default="inproc",
                    help="inproc = timed pipeline breakdown; subproc = total time only (python -m ...)")
    ap.add_argument("--lines", type=int, nargs="+", default=[1, 10, 100, 1_000, 10_000],
                    help="program sizes (number of identical lines)")
    ap.add_argument("--iters", type=int, default=50, help="timed iterations per size")
    ap.add_argument("--warmup", type=int, default=10, help="warmup iterations per size")
    ap.add_argument("--module", default="bang.cli",
                    help="module for subproc mode (default: bang.cli)")
    args = ap.parse_args()

    os.environ.setdefault("PYTHONHASHSEED", "0")

    print(f"\nBang E2E benchmark | mode={args.mode} | iters={args.iters} | warmup={args.warmup}\n")

    rows = []

    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)

        for n in args.lines:
            bang_file = write_program(tmpdir, n)

            if args.mode == "inproc":
                series = measure_inproc(bang_file, args.iters, args.warmup)

                # total stats
                tmin, tmed, tp95, tmax = summarize(series["total"])
                per_line = tmed / n
                lps = (1.0 / per_line) if per_line > 0 else float("inf")

                row = {
                    "lines": n,
                    "total_min": tmin,
                    "total_med": tmed,
                    "total_p95": tp95,
                    "total_max": tmax,
                    "per_line_med": per_line,
                    "lines_per_sec_med": lps,
                }

                # phase medians
                for phase in ("lex", "expr_split", "expr_load", "cf", "sem", "eval"):
                    _, pmed, _, _ = summarize(series[phase])
                    row[f"{phase}_med"] = pmed

                rows.append(row)

            else:
                total_times = measure_subproc_total_only(bang_file, args.iters, args.warmup, args.module)
                tmin, tmed, tp95, tmax = summarize(total_times)
                per_line = tmed / n
                lps = (1.0 / per_line) if per_line > 0 else float("inf")
                rows.append({
                    "lines": n,
                    "total_min": tmin,
                    "total_med": tmed,
                    "total_p95": tp95,
                    "total_max": tmax,
                    "per_line_med": per_line,
                    "lines_per_sec_med": lps,
                })

    print_total_table(rows)

    if args.mode == "inproc":
        print_phase_table(rows)
    else:
        print("\nNote: subprocess mode reports TOTAL only (includes Python startup/import).\n")


if __name__ == "__main__":
    main()
