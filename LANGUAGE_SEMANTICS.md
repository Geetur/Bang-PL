# Bang semantics after stabilization

These rules describe the current implementation. They make the corrected behavior explicit before further language features are added.

## Values and operators

- Numbers support ordinary real-number arithmetic. Booleans participate in numeric operations as 1 and 0. Boolean literals retain the existing numeric representation; predicate results may display as `True` or `False` while behaving numerically in arithmetic, iteration bounds, indexing and repetition.
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

## Functions and scopes

- Function interfaces compose explicitly. `fn f args` receives positional arguments as one array. `fn f args {frozen = false}` keeps every positional value in `args` and binds the declared options only by name: `f{1,2,frozen=true}` gives `args=[1,2]` and `frozen=true`. Defaults can reference the argument array. The array name cannot also be an option name or be supplied as a named argument.
- `fn f {input, frozen = false}` remains available for a fixed signature: it accepts positional or named bindings for its individual parameters. `fn f {}` accepts no arguments. Builtins, record constructors and the plain `fn f args` form remain positional-only.
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

## Checking and diagnostics

- The checker records an operation's result type, not the type or literal shape of its RHS. It updates/invalidate facts when indexed/field mutation or aliases make earlier information stale.
- Control-flow joins preserve record aliases shared on every path. Uncertain sharing is treated conservatively, and writes through unknown references invalidate potentially affected mutable facts.
- Unknown user calls invalidate potentially changed facts. Runtime checks validate values that cannot be determined statically. This is a best-effort checker, not a claim of complete static type safety.
- Expressions use explicit stacks for checking and evaluation, so long flat arithmetic trees and call/index/field chains do not consume the Python call stack.
- `Evaluator.MAX_CALL_DEPTH`, `ExpressionParser.MAX_EXPRESSION_DEPTH`, and `ControlFlowParser.MAX_BLOCK_DEPTH` default to 64. They bound nested function invocations, recursive collection/call parsing, and nested control blocks. Parentheses handled iteratively and flat operator chains do not consume the recursive-parser limit. Excess nesting produces a Bang diagnostic.
- Integer literals are limited to 4,300 digits. Numeric literals use ASCII digits. Source files use UTF-8; NUL and raw newlines inside string literals are rejected. Escaped-string syntax is not introduced by this patch.
- Error line numbers are one-based. Missing/unreadable source files are reported as file errors.
