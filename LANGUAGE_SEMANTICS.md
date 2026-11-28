# Bang language semantics (v0.1)

These rules describe the current v0.1 interpreter, including its syntax, numeric compatibility, evaluation order, builtins, and diagnostic limits.

## Values and operators

- Numbers support ordinary real-number arithmetic. Booleans participate in numeric operations as 1 and 0. Boolean literals retain the existing numeric representation. All boolean output is `1` or `0`, including predicate results in interpolation and nested containers. Booleans behave numerically in arithmetic, iteration bounds, indexing, and repetition.
- `none`, an omitted record field, a function that falls through, and the return value of `print` are all represented by zero. In particular, `none == 0`, `false == 0`, and `true == 1` remain true.
- Strings support concatenation with `+`, removal of every matching substring with `-`, splitting into an array with `/`, and repetition with an integer multiplier. An empty split separator produces individual characters.
- Array `+` concatenates. Array `-` removes matching elements, including nested arrays. Array `*`, `/`, and `//` pair corresponding elements and broadcast a singleton operand. Other unequal lengths are errors.
- Multiplying an array by an integer repeats each element, in order: `[1,2] * 2` produces `[1,1,2,2]`. Each repeated mutable value is copied independently. Function values and constructor declarations retain their identity when copied.
- Set `+` is union and `-` is difference. Set comparisons use subset/superset relationships. Dictionary `+` merges, with the right-hand value winning duplicate keys; dictionary `-` removes keys appearing on the right.
- Array ordering is lexicographic. Functions, constructor declarations and mutable record instances compare by identity. They can be used as identity keys in sets and dictionaries. Numeric/string/array/set/dictionary comparisons retain their existing value behavior.
- Invalid operand combinations, division/domain failures, non-finite real results, and unsupported complex results produce Bang diagnostics. They do not expose a Python traceback.

## Evaluation order and assignment

- Binary expressions evaluate their left operand before their right operand. `&&` and `||` return a selected operand and skip the right operand when the left decides the result.
- Calls resolve the callee before evaluating arguments, then evaluate arguments from left to right. Calling a builtin uses the resolved value, including through aliases and rebinding.
- Index reads evaluate their base first, then each index in order. An invalid earlier index stops evaluation before later indexes. Field/index/call chains use these same rules.
- Ordinary assignment evaluates the RHS first and then resolves its targets. Compound assignment resolves and reads a scalar target once, evaluates the RHS once, and stores the corresponding operator result back to that location.
- Destructuring evaluates the RHS once and writes targets from left to right. Nested targets are supported. The RHS must supply at least as many values as the targets at each level; extra values are ignored, preserving the existing behavior.
- Compound destructuring applies the corresponding operator to each target and RHS item.
- Array `+=` computes and reassigns a concatenated array. Other variables referencing the earlier array keep that earlier array.
- Assignment is a statement. Assignment expressions and chained assignment are rejected. Inside a call, `name = expression` is a named argument label and never assigns a caller variable.

## Indexing, slices, and multiline expressions

- `g[i,j,k]` is exactly nested access `g[i][j][k]`. Both spellings support reads, assignment, and compound assignment. Each selector evaluates once, then its access completes before the next selector evaluates. A failed access skips later selectors. Levels are one-based in diagnostics; arrays may be ragged.
- Ordinary array and string indexes must be integers. Negative indexes count from the end; out-of-range ordinary indexes are errors. Dictionaries accept hashable keys. A single trailing comma is allowed: `g[i,]` means `g[i]`.
- Slices have the form `[start:stop:step]`, with an exclusive stop. The step defaults to 1 and cannot be zero. Bounds and steps must be integers. Boolean numeric compatibility applies. An explicit `none` is zero, distinct from an omitted bound.
- With a positive step, omitted start and stop mean 0 and the sequence length. With a negative step, they mean the final index and the position before the first element. Negative explicit bounds are offset from the end, then bounds are clamped. An incompatible direction produces an empty slice. In particular, `a[::-1]` reverses while `a[:-1:-1]` is empty.
- Array and string slice reads work, including on empty sequences. Array slices copy the outer array and retain references to nested values. Strings are immutable.
- Slice assignment requires an array target and array replacement. A step of 1 permits insertion, deletion, and resizing. Other steps, including negative steps, require exactly as many replacement values as selected positions. Aliased replacement values are handled safely. Compound slice assignment uses the existing operators and assignment order.
- A comma selector list cannot contain slices. `g[:,1]` is rejected; it does not select a column. Explicit chaining such as `g[:][1]` or `g[1][::-1]` retains its ordinary meaning.
- Newlines inside balanced `{}`, `[]`, and `()` continue the expression. Commas remain required between values; one trailing comma is supported in arrays, calls, parameter lists, and ordinary index lists. Semicolons are statement separators only outside groups. Comments outside strings extend to the physical line end.
- `for [name,score] results` destructures each row using the existing assignment rules. Nested targets, record fields, and indexed targets work inside the destructuring pattern. Each row must provide enough values at every unpacking level; extra values are ignored. Loop/branch scope and control-transfer rules remain unchanged.

## Strings and interpolation

- Both ordinary and interpolated double-quoted strings decode `\n`, `\r`, `\t`, `\b`, `\f`, `\v`, `\"`, `\'`, and `\\`. Unknown escapes raise a lexer error at the backslash; `\x41`, `\u0041`, and octal escapes are not implemented. Write UTF-8 characters directly or escape a literal backslash.
- Strings occupy one physical source line. Escaped `\n` adds a newline value without changing the physical source location of later tokens. Raw newlines and NUL characters in source strings are rejected.
- Only an immediate lowercase `f"` starts interpolation. Ordinary strings keep all braces literal. In interpolated strings, `{{` and `}}` produce literal braces and `{expression}` evaluates a Bang expression.
- Fields allow ordinary calls, indexing, slices, function expressions, nested strings, and nested interpolated strings. Quoted strings inside a field may use the same double quote as the outer string. Empty fields, unmatched delimiters, raw newlines, and comments in fields are errors. Conversion flags and format specifications are not supported.
- Fields evaluate once, left to right. Each result is formatted immediately before the next field runs, so later mutations do not change text already emitted by an earlier field. A failed field skips later fields.
- Printing and interpolation share one formatter. Top-level strings are verbatim; strings inside containers/records are quoted. All boolean values print as 1/0 and all `none` values as 0. Functions display their diagnostic name or definition line, builtins their Bang name, constructors their name/schema, and instances their type and named fields. Cycles are marked with `...`; shared acyclic values are printed fully.

## Functions and scopes

- Named block functions retain `fn name interface` followed by statements and `end`. Named short functions use `fn name interface return expression` with no `end`. Anonymous functions use `fn interface return expression` in expression position. All three existing interfaces work: an argument-array name, `{parameters}`, or an argument-array name followed by `{named options}`.
- In expression position an identifier after `fn` is the argument-array name. `f=fn power {x} return x` therefore collects positional values in `power` and requires the named option `x`; use `f=fn {x} return x` for a fixed parameter.
- A short body is one explicit return expression, ending at its enclosing statement/comma/closing-delimiter boundary or EOF. Nested groups remain part of the body. Short functions have no implicit branching or conditional expression. Named and anonymous functions use the same closure, default, and call rules.

- Function interfaces compose explicitly. `fn f args` receives positional arguments as one array. `fn f args {frozen = false}` keeps every positional value in `args` and binds the declared options only by name: `f{1,2,frozen=true}` gives `args=[1,2]` and `frozen=true`. Defaults can reference the argument array. The array name cannot also be an option name or be supplied as a named argument.
- `fn f {input, frozen = false}` remains available for a fixed signature: it accepts positional or named bindings for its individual parameters. `fn f {}` accepts no arguments. Builtins use the input/options interfaces specified below. Record constructors and the plain `fn f args` form remain positional-only.
- Declared parameter names must be unique. Required parameters precede defaulted parameters. Positional arguments precede named arguments. Unknown names, duplicate bindings, missing required arguments and excess positional arguments produce Bang diagnostics, including through aliases, fields, indexes and returned functions.
- Supplied argument expressions evaluate left to right in source order, after the callee. Omitted defaults evaluate once per invocation in parameter order, before the body. Defaults see the function's captured scopes and earlier parameters. They cannot refer to themselves or later parameters. Every declared parameter shadows captured bindings of the same name.
- Defaults apply only when an argument is omitted. Explicit zero, `false` and `none` remain supplied values. Mutable default expressions such as `[]` create a fresh value each time they are evaluated; a default expression referencing an existing captured array retains that array's normal reference behavior.
- A function captures references to the scope dictionaries visible at its definition. Assigning an existing captured binding persists across calls. Mutating captured containers also persists. Separate factory calls retain separate local scope dictionaries.
- Each invocation has a new parameter frame. Its named argument-array parameter shadows any captured binding of the same name.
- Assignment updates the nearest existing binding, otherwise creates a binding in the current scope. This preserves Bang's existing assignment lookup rule.
- Blocks create the same scopes during checking and execution. A branch-local or loop-local binding is not available after its scope exits, although a returned/stored closure can keep that scope alive.
- `break` and `continue` belong to loops in the current function; they cannot escape into a caller's loop. Every exit path restores scope/depth bookkeeping.
- The checker validates names in declaration order. Captured values and user-call effects are treated conservatively; they are not assumed to retain the types they had when a function was defined.

Example closure:

```text
fn make args
    n = 0
    fn next ignored
        n += 1
        return n
    end
    return next
end
c = make{}
print{c{}, c{}}   # 1 2
```

## Records and control flow

- A constructor is a value and can be returned, indexed, aliased, or stored in a field. Every constructor call checks arity at runtime; omitted fields default to zero and extra arguments are rejected.
- Instances retain their original declaration/schema even if the variable naming that constructor is reassigned or redeclared.
- An `if` may have multiple `elif` branches and at most one final `else`. The entire chain has one closing `end`. An `elif` or `else` header switches the active branch of the current open `if`; it does not open another block. An `else` header contains only `else`, and no `elif` may follow it. Branch bodies may be empty.
- Each nested `if`, `for`, `while`, or `fn` still needs its own `end`. An `elif` or `else` attaches to the innermost open block only if that block is an `if`; close an inner loop or function before continuing the surrounding conditional. Missing endings identify the innermost unfinished block's header.
- Only the first matching branch executes. Later conditions and bodies are skipped. Branch-local bindings do not escape the branch; assignments to existing enclosing bindings retain their existing behavior.
- Integer for-bounds iterate from zero toward the bound, excluding the bound. Predicate booleans work like the corresponding integer bounds.
- For-loops traverse the original collection. Changing dictionary keys during traversal produces a Bang diagnostic if the iterator is advanced again. Updating existing values is allowed; breaking immediately after adding a key is also allowed.

```bang
score = 85
if score >= 90
    print{"A"}
elif score >= 80
    print{"B"}
else
    print{"C"}
end
```

## Builtins

- Every builtin declares inputs, named options, and aliases in one shared interface registry. Checking and execution use the same binder. The resolved callable controls behavior, including through aliases, rebinding, containers, and callbacks. Labels do not become data or caller assignments. Supplied argument and option expressions evaluate once in source order before binding; positional arguments precede names.
- A positional input and `input=...` are equivalent. Supplying both is an error, as are duplicate aliases or unknown options. Options must be declared for that builtin. Boolean flags accept integer/boolean 0 or 1, including Bang's `none` numeric zero. Other values are errors. Optional callbacks, when explicitly supplied, must be callable; omit them rather than passing zero/none.
- `sum` requires one iterable. `set` requires one iterable when provided; `set{}` creates an empty set. `sum{1,2}`, `set{1,2}`, `sum{1}`, and `set{1}` are errors. Use arrays for multiple data values. `sum{[]}` is zero. Strings iterate over characters, dictionaries over keys, and arrays/sets/frozen sets over elements. There are no implicit numeric ranges from scalar inputs.
- `print` retains variadic values. `dict` retains alternating key/value positional arguments. `min`, `max`, and `sort` retain positional value lists, and accept one iterable input; a single non-iterable scalar is treated as one item. `sort` returns an array. `range{start,stop,step}` and `range{[start,stop,step]}` remain explicit constructor exceptions to the one-input rule.
- `print` options are `sep=" "`, `end="\n"`, `flush=false`, and `spread=false`. `sep` and `end` must be strings. `spread=true` expands one iterable input into printed items; ordinary array printing retains brackets. `print{}` still outputs a newline and returns zero. `end` is permitted as a contextual named-argument label, while remaining a block keyword elsewhere.
- `len{input,where=callback}` counts items whose callback result is truthy. Without `where`, it returns the ordinary length. A `where` callback receives one item.
- `int{input,base=10}` converts numeric values by truncation toward zero. Strings permit surrounding whitespace, an optional sign, and ASCII digits/letters appropriate for bases 2 through 36. `base=0` uses radix prefixes; applicable `0x`, `0o`, and `0b` prefixes are supported. Underscores, decimal points, non-ASCII digits, and more than 4,300 digits are rejected. A non-decimal base requires string input. Numeric boolean/none compatibility remains intact.
- `input{}` reads one line; `input{prompt}` and `input{input=prompt}` are equivalent. `prompt=` aliases `input=`. The prompt must be a string. The final newline is removed; `strip=true` also removes surrounding whitespace. The prompt is written once, and EOF/stream errors produce Bang diagnostics.
- `sum{input,initial=value,transform=callback}` folds the normal Bang `+` operation over items, optionally transforming each item once. Without an explicit initial value, nonempty input uses the corresponding empty numeric/string/array/set/dictionary identity; a frozen first item produces a frozen-set identity. Empty input without an initial value returns numeric zero. An explicit initial value is preserved for empty input. Transform callbacks receive one item.
- `set{input,frozen=false,transform=callback}` optionally transforms each item once, then requires hashable results and removes duplicates. `frozen=true` returns an immutable, hashable set container. Nested records remain mutable identity-hashed values; freezing is shallow. Readable output is `frozen{...}`. `set{frozen=true}` is an empty frozen set. A set itself must be frozen to serve as a set member or dictionary key.
- Set and frozen-set union/difference return the left operand's kind. Equality compares contents across both kinds; ordering remains subset/superset comparison. Frozen sets support membership, iteration, lengths, arithmetic aggregation, and collection copies, but not indexed or field mutation. Array repetition retains its existing deep-copy rules for nested values.
- `dict` accepts a mapping copy, an array of `[key,value]` pairs, a flat key/value array, or alternating positional keys/values. `values=iterable` instead zips input keys with those values and requires equal lengths. Without `values`, a standalone string is not a pair collection. `strict=false` keeps the final value for a repeated key; `strict=true` rejects duplicates. Keys must be hashable. Copies retain references to nested values.
- `min`/`max` support `key=callback` and `default=value`. A key callback receives each original item once, and the selected original item is returned. Ties keep the first item. Empty input returns an explicitly provided default or raises an error. An unused default is still an ordinary eagerly evaluated argument expression.
- `sort` supports `key=callback`, `reverse=false`, and `in_place=false`. Keys are evaluated once per item in traversal order, and sorting is stable. The default is a new array. `in_place=true` requires one array input; successful sorting replaces its outer contents and returns that same array. Sorting failure does not commit a reordered array, but effects already performed by user callbacks persist.
- `range{input=stop,start=0,step=1,inclusive=false}` constructs an array of integers. `stop=` aliases `input=`. The step must be nonzero. Inclusive bounds include the stop only when reached by the step; they do not append an otherwise unreachable value. Duplicate start/step values supplied through both a positional range specification and options are errors. `range{}` remains an empty range.
- `map{input,transform=callback}` returns callback results. `filter{input,predicate=callback}` returns the original items with truthy results; `invert=true` selects falsy results. Their callbacks receive one item, or `item,index` when `indexed=true`. Indexes are zero-based positions in the input traversal, including dictionary-key and set traversal.
- `reduce{input,combine=callback,initial=value}` is a left fold. Its callback receives `accumulator,item`, or `accumulator,item,index` with `indexed=true`. Without an initial value, the first item seeds the accumulator and callbacks begin at original index 1. Empty input requires an initial value, which is returned unchanged. A singleton without an initial value does not invoke the callback.
- Map/filter/reduce also accept the callback as the second positional argument. The earlier callback-first spelling remains accepted when the first argument is callable and the second iterable, with no named input also present. Unknown types are deferred conservatively by the checker. Mixed positional/named duplicates are rejected; there is no reinterpretation that silently discards data.
- Callback-driven builtins snapshot the outer iterable contents after all argument expressions evaluate, then traverse in iteration order. Nested values remain shared references. A failure skips later callbacks. Callback effects and explicit in-place sorting invalidate potentially stale checker facts. Sets have no promised iteration order. Callback arity is checked when actually invoked, including ordinary callable constructors and builtin callbacks.

## Checking and diagnostics

- The checker records an operation's result type, not the type or literal shape of its RHS. It updates/invalidate facts when indexed/field mutation or aliases make earlier information stale.
- Control-flow joins preserve record aliases shared on every path. Uncertain sharing is treated conservatively, and writes through unknown references invalidate potentially affected mutable facts.
- Unknown user calls invalidate potentially changed facts. Runtime checks validate values that cannot be determined statically. This is a best-effort checker, not a claim of complete static type safety.
- Expressions use explicit stacks for checking and evaluation, so long flat arithmetic trees and call/index/field chains do not consume the Python call stack.
- `Evaluator.MAX_CALL_DEPTH`, `ExpressionParser.MAX_EXPRESSION_DEPTH`, and `ControlFlowParser.MAX_BLOCK_DEPTH` default to 64. They bound nested function invocations, recursive collection/call parsing, and nested control blocks. Parentheses handled iteratively and flat operator chains do not consume the recursive-parser limit. Excess nesting produces a Bang diagnostic.
- Integer literals are limited to 4,300 digits. Numeric literals use ASCII digits. Source files use UTF-8; NUL and raw newlines inside string literals are rejected. String escape and interpolation rules are specified above.
- Error line numbers are one-based. Missing/unreadable source files are reported as file errors.

- Index errors identify the failed selector, its level, and the current length when applicable. Field errors identify the failed field and list available fields. Slice errors identify the bad bound or mismatched replacement lengths. Diagnostic construction never re-evaluates a selector or callback.
