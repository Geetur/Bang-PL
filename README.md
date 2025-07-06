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
