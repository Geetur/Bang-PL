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
- Assignment is a statement. Assignment inside a call, condition, array or return expression, and chained assignment, is rejected rather than hoisted into a different statement.

## Functions and scopes

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
- An if may have multiple elif branches and at most one final else. Each dependent branch uses its existing `end`, followed by the owning if's final `end`. An else header contains only `else`.
- Integer for-bounds iterate from zero toward the bound, excluding the bound. Predicate booleans work like the corresponding integer bounds.

## Checking and diagnostics

- The checker records an operation's result type, not the type or literal shape of its RHS. It updates/invalidate facts when indexed/field mutation or aliases make earlier information stale.
- Unknown user calls invalidate potentially changed facts. Runtime checks validate values that cannot be determined statically. This is a best-effort checker, not a claim of complete static type safety.
- Expressions use explicit stacks for checking and evaluation, so long flat arithmetic trees and call/index/field chains do not consume the Python call stack.
- `Evaluator.MAX_CALL_DEPTH`, `ExpressionParser.MAX_EXPRESSION_DEPTH`, and `ControlFlowParser.MAX_BLOCK_DEPTH` default to 64. They bound nested function invocations, recursive collection/call parsing, and nested control blocks. Parentheses handled iteratively and flat operator chains do not consume the recursive-parser limit. Excess nesting produces a Bang diagnostic.
- Integer literals are limited to 4,300 digits. Numeric literals use ASCII digits. Source files use UTF-8; NUL and raw newlines inside string literals are rejected. Escaped-string syntax is not introduced by this patch.
- Error line numbers are one-based. Missing/unreadable source files are reported as file errors.
