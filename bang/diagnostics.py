"""Source rendering and bounded diagnostic descriptions; never evaluate Bang code."""

from dataclasses import replace

from bang.lexing.lexer_tokens import SYMBOLS


def render_error(kind, text, message, row, start, end=None):
    lines = text.removesuffix("\0").splitlines()
    source = lines[row - 1] if 0 < row <= len(lines) else ""
    # Preserve tabs in the pointer prefix so it aligns with the displayed source.
    prefix = "".join("\t" if char == "\t" else " " for char in source[: start - 1])
    prefix += " " * max(0, start - 1 - len(source))
    width = 1 if end is None else max(1, end - start)
    width = min(width, max(1, len(source) - start + 1))
    columns = str(start) if end is None else f"{start}-{end}"
    return (
        f"[{kind}] Line {row}, Column {columns}:\n"
        f"{source.rstrip()}\n{prefix}{'^' * width}\n{message}"
    )


def source_span(tokens):
    first = tokens[0]
    end = first.column_end
    for token in tokens:
        if token.line != first.line:
            break
        end = max(end, token.column_end)
    return replace(first, column_end=end)


def expression_location(expression, fallback=None):
    return (
        getattr(expression, "meta_data", None)
        or getattr(getattr(expression, "root_expr", None), "meta_data", None)
        or fallback
    )


def index_location(node, position):
    return expression_location(node.index[position], node.meta_data)


def field_location(node, position):
    return (
        node.field_meta_data[position] if position < len(node.field_meta_data) else node.meta_data
    )


_TYPE_NAMES = {
    "int": "number",
    "float": "number",
    "bool": "boolean",
    "str": "string",
    "list": "array",
    "dict": "dictionary",
    "set": "set",
    "frozenset": "frozen set",
    "NoneType": "none",
    "runtime_function": "function",
    "runtime_builtin": "builtin function",
    "runtime_dataclass": "record constructor",
    "runtime_instance": "record",
    "NumberType": "number",
    "BoolType": "boolean",
    "StringType": "string",
    "ArrayType": "array",
    "DictType": "dictionary",
    "SetType": "set",
    "FrozenSetType": "frozen set",
    "FunctionType": "function",
    "BuiltinType": "builtin function",
    "DataClassType": "record constructor",
    "InstanceType": "record",
    "DynamicType": "value",
    "SliceType": "slice",
    "slice": "slice",
}


def type_name(value):
    return _TYPE_NAMES.get(type(value).__name__, "value")


def diagnostic_value(value):
    """Avoid huge strings, integer conversion limits, and recursive object reprs."""
    if type(value) is str:
        return repr(value[:60]) + ("..." if len(value) > 60 else "")
    if type(value) is bool:
        return "1" if value else "0"
    if type(value) in (int, float, bool):
        try:
            if type(value) is int and value.bit_length() > 256:
                return "<large integer>"
            return str(value)
        except (ValueError, OverflowError):
            return "<number>"
    return f"<{type_name(value)}>"


def nonindexable_message(base, level):
    return (
        f"cannot index {type_name(base)} at level {level}; expected an array, string, or dictionary"
    )


def index_error_message(error, base, key, level, *, writing=False, value=None):
    if writing and type(base) is str:
        return f"cannot assign to string index at level {level}; strings are immutable"
    if type(base) not in (list, str, dict):
        return nonindexable_message(base, level)
    if isinstance(key, slice):
        if type(base) is dict:
            return f"slicing requires an array or string at level {level} (got dictionary)"
        if writing and isinstance(error, ValueError):
            count = len(range(*key.indices(len(base))))
            return (
                f"extended slice assignment length mismatch at level {level} "
                f"(expected {count} values, got {len(value)})"
            )
        return f"invalid slice at level {level}"
    if isinstance(error, IndexError):
        return f"index {diagnostic_value(key)} out of bounds at level {level} (length {len(base)})"
    if isinstance(error, KeyError):
        return f"key {diagnostic_value(key)} not found at level {level}"
    if type(base) is dict:
        return f"dictionary key at level {level} must be hashable (got {type_name(key)})"
    detail = " " + diagnostic_value(key) if type(key) in (int, float, bool, str) else ""
    return (
        f"{type_name(base)} index at level {level} must be an integer "
        f"(got {type_name(key)}{detail})"
    )


def field_error_message(base, name):
    fields = getattr(base, "fields", None)
    if type_name(base) != "record":
        note = "; use indexing for dictionary keys" if type_name(base) == "dictionary" else ""
        return f"cannot access field '{name}' on {type_name(base)}{note}"
    available = ", ".join(list(fields)[:12]) if fields else "(none)"
    if fields and len(fields) > 12:
        available += ", ..."
    record = getattr(getattr(base, "of", None), "name", "record")
    return f"{record} has no field '{name}'; available fields: {available}"


_OPERATOR_TEXT = {value: symbol for symbol, value in SYMBOLS.items()}


def operator_message(op, left, right):
    symbol = _OPERATOR_TEXT.get(op, "?")
    return f"operator '{symbol}' does not support {type_name(left)} and {type_name(right)}"
