# Bang – A Minimalistic Array-Centric Scripting Language

> **Built for prototyping. No ceremony.**

This repository is a **from-scratch reference implementation** of **Bang**, a small scripting language you can read, hack, and extend in a single afternoon. The codebase walks a Bang program through every classic compiler/interpreter stage—**lexing → expression parsing → control-flow parsing → static (semantic) analysis → evaluation**—all in ~2.5 kLOC of tidy, commented Python.

![alt text](Bang.png)
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
Bang was born as a teaching/portfolio project: a **fully-featured yet bite-sized language** that proves mastery over parsing, static analysis, runtime design, and project architecture—without the 50 kLOC overhead of a “real” compiler. Every stage is separately implemented and individually testable, so you can observe _exactly_ how code is transformed step by step. 

## Key Language Features
* **Array-first syntax** with intuitive overloading:  
  `[1,2,3] + [4]`, `[1,2,3] / [5]`, `[1,2,3] / [4,5,6]`, `[1,2,3] * 2`, and `[a,b,c] = [1, 2, 3]`  to append, element-wise divise, duplicate, and multi-initialize respectivley.
* Familiar operators `+ - * / // **`, Boolean logic `&&`, `||`, unary `!`, and compound assignments `+=`, `-=`, …
* Tiny but expressive **control flow** (`if / elif / else`, `for`, `while`, `break`, `continue`).
* **First-class functions** with variadic argument lists passed as a single named array (ex. args).
* **Built-ins**: `print`, `len`, `sum`, `min`, `max` — super easy to extend, essentially just have to write a function defining the behaviour.
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
git clone https://github.com/Geetur/Bang-PL.git
cd Bang-PL

# 2. (Optional) Create a virtualenv

# Unix/macOS
python -m venv .venv
source .venv/bin/activate

# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1

# 3. Install Bang and dev dependencies (as defined in pyproject.toml)
#    This installs the `bang` console script plus ruff, pre-commit, and pytest
pip install -e .[dev]

# 4. Set up Git hooks (configured in .pre-commit-config.yaml)
#    Installs pre-commit hooks for linting via ruff
pre-commit install

# After this step you should have a bang console‑script on your PATH. If not, fall back to python ‑m bang.
```
Python 3.10+ is required (pattern-matching FTW).

## Running Bang Code
If you followed the getting started (installed -e) you can write:
```
# this is an example! use whatever file path you want!
bang examples\input2.bang
```
in your terminal to run whatever bang program you want.

if not, write:

```
python -m bang examples\input2.bang
```
which will work regardless if you installed .e or not!


## Examples! 

# 1. the first program
Input:
```
print{"Hello, Bang!"}
# I wonder what it does!
```

Output:
```
Hello, Bang!
```

# 2. solution to two sum
   
```
fn two_sum args

    [target, input] = [args[0], args[1]]
    [ans, seen] = [[], set{}]
    for i input
        if target - i in seen
            ans += [[target - i, i]] 
            end
        seen += set{i} 
        end
    return ans 
    end

print{two_sum{8, [1,2,3,4,5,6,7,]}}
```
Output:
```
[[1,7], [2,6], [3,5]]
```
# 3. printing n fibonacci numbers
```
# printing n fibonacci numbers

fn fib awesome
    ret = []
    [n, a, b] = [awesome[0], 0, 1]
    ret += [a, b]
    for i n-2
        c = a + b ; [a,b] = [b, c]
        ret += [c]
    end
    return ret
end
fib{9}

```
output:
```
[0,1,1,2,3,5,8,13,21]
```
## 4. house robber (for the dp gods)
```
fn rob args
    nums = args[0]

    if len{nums} <= 2
        return max{nums}
    end

    nums[-2] = max{nums[-1], nums[-2]}

    for i range{len{nums} - 3, -1, -1}
        nums[i] = max{nums[i] + nums[i + 2], nums[i + 1]}
    end

    return nums[0]
end

print{rob{[2,7,9,3,1]}}

```
output:
```
12
```
## 5. recursive factorial
```
fn fact args
    n = args[0]
    acc = args[1]  # accumulator defaults to 1 at top call
    if n <= 1
        return acc
    end
    return fact{n - 1, acc * n}
end

print{fact{6, 1}} 

```

output: 
```
720
```

## Running the Test-Suite
```
pytest bang\semantic\semantic_tests.py
```
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

* I really tried to make anything possible in bang, if you simply add a built-in function in the evaluator to support the behaviour.

Tip: Each phase is cleanly decoupled; you can unit-test a new feature in isolation before wiring up the next stage.

## Project Roadmap

* Add way more built-in functions (this is really easy you should try it)

* Classes and dataclasses

* Interpret in c++ or similar for faster runtimes

* REPL with auto-completion

## Contributing

PRs and issue reports are welcome! Please run pytest and ruff (optional for now since ruff isn't a dependency) (or your formatter of choice) before opening a pull-request.

* Fork the repo

* Create your feature branch: git checkout -b feat/my-cool-thing

* Commit your changes: git commit -m "feat: my cool thing"

* Push to the branch: git push origin feat/my-cool-thing

* Open a PR 🥳

## License
MIT © 2025 Jeter Pontes
See LICENSE for full text.
