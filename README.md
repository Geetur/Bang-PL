# Bang – A Minimalistic Array-Centric Scripting Language

> **Built for learning. Written for fun. Tested for correctness.**

This repository is a **from-scratch reference implementation** of **Bang**, a small scripting language you can read, hack, and extend in a single afternoon. The codebase walks a Bang program through every classic compiler/interpreter stage—**lexing → expression parsing → control-flow parsing → static (semantic) analysis → evaluation**—all in ~2 kLOC of tidy, commented Python.

---

## Table of Contents
1. [Motivation](#motivation)  
2. [Key Language Features](#key-language-features)  
3. [Architecture Overview](#architecture-overview)  
4. [File / Module Guide](#file--module-guide)  
5. [Getting Started](#getting-started)  
6. [Running Bang Code](#running-bang-code)  
7. [Running the Test-Suite](#running-the-test-suite)  
8. [Extending the Language](#extending-the-language)  
9. [Project Roadmap](#project-roadmap)  
10. [Contributing](#contributing)  
11. [License](#license)  

---

## Motivation
Bang was born as a teaching/portfolio project: a **fully-featured yet bite-sized language** that proves mastery over parsing, static analysis, and runtime design—without the 50 kLOC overhead of a “real” compiler. Every stage is separately implemented and individually testable, so you can observe _exactly_ how code is transformed step by step.

## Key Language Features
* **Array-first syntax** with intuitive overloading:  
  `arr - 3`, `3 - arr`, `arr - arr2`, and `arr / 4` to chunk.
* Familiar operators `+ - * / // **`, Boolean logic `&&`, `||`, unary `!`, and compound assignments `+=`, `-=`, …
* Tiny but expressive **control flow** (`if / elif / else`, `for`, `while`, `break`, `continue`).
* **First-class functions** with variadic argument lists passed as a single `args` array.
* **Built-ins**: `print`, `len`, `sum`, `min`, `max` — easy to extend.
* **Strong static guarantees** before runtime: undefined variables, invalid operators, out-of-scope `break`, etc. are caught by the semantic pass.

## Architecture Overview
┌────────┐ ┌──────────────────┐ ┌────────────────┐ ┌──────────────┐ ┌────────────┐
│ Source │ → │ Lexer (tokens) │ → │ Expression-SYA │ → │ Blockenizer │ → │ Semantics │ → Evaluator
└────────┘ └──────────────────┘ └────────────────┘ └──────────────┘ └────────────┘
^ ^ ^ ^
│ each pass guarantees invariants & raises rich error objects

| Path | Responsibility |
|------|----------------|
| `lexer.py` | Tokenises `.bang` files. |
| `expression_parser.py` | Builds per-line ASTs, resolves unary/binary ambiguity, handles function calls. |
| `control_flow_parser.py` | Converts flat node list into nested blocks (`if`, `for`, etc.). |
| `parser_nodes.py` | All immutable AST node dataclasses (shared). |
| `semantic_analysis.py` | Static checker; defines lightweight _type objects_. |
| `evaluator.py` | Runtime evaluator with built-in functions and array semantics. |
| `evaluator_nodes.py` | Runtime-only constructs (currently just `RuntimeFunction`). |
| `*_tests.py` | Pytest suites exercising semantics & runtime. |

## Getting Started
```bash
# 1. Clone
git clone https://github.com/your-handle/bang.git
cd bang

# 2. (Optional) Create a virtualenv
python -m venv .venv
source .venv/bin/activate

# 3. Install dev dependencies
pip install -r requirements.txt  # mainly pytest & rich-traceback
Python 3.10+ is recommended (pattern-matching FTW).

Running Bang Code
There isn’t a one-liner CLI yet, but you can run a Bang file in three lines of Python:

from lexer import Lexer
from expression_parser import ExpressionParser
from control_flow_parser import ControlFlowParser
from semantic_analysis import SemanticAnalysis
from evaluator import Evaluator

src = "examples/hello.bang"
lex = Lexer(src); tokens = lex.tokenizer()
ex  = ExpressionParser(tokens, lex.file); ex.split(); ex.loading_into_algos()
cf  = ControlFlowParser(lex.file, ex.post_SYA); roots = cf.blockenize()
SemanticAnalysis(lex.file, roots).walk_program()  # static checks
Evaluator(lex.file, roots).eval_program()         # run it!
Minimal example (hello.bang)

Input:
print{"Hello, Bang!"}
# I wonder what it does!

Output:
Hello, Bang!

## Running the Test-Suite
pytest -q
The suite contains hundreds of assertions split across:

* lexer_tests.py

* parser_expression_tests.py

* semantic_tests.py – must not raise SemanticError for valid programs, and must raise for invalid ones.

* evaluator_tests.py – checks runtime behaviour & error handling (EvaluatorError).

## Extending the Language

* Add tokens in lexer.py & grammar tweaks in expression_parser.py.

* Teach semantic_analysis.py the new static rules.

* Implement runtime semantics in evaluator.py.

* Add green- & red-path tests—then refactor fearlessly.

Tip: Each phase is cleanly decoupled; you can unit-test a new feature in isolation before wiring up the next stage.

## Project Roadmap

 CLI runner (bang run file.bang)

 Interpret in c++ or similar for faster runtimes

 REPL with auto-completion

 Standard library (stats, maybe sockets?)

## Contributing

PRs and issue reports are welcome! Please run pytest and ruff (or your formatter of choice) before opening a pull-request.

* Fork the repo

* Create your feature branch: git checkout -b feat/my-cool-thing

* Commit your changes: git commit -m "feat: my cool thing"

* Push to the branch: git push origin feat/my-cool-thing

* Open a PR 🥳

License
MIT © 2025 Dan James
See LICENSE for full text.
