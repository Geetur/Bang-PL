"""Best-effort builtin checks using the same interfaces as runtime binding."""

from bang.builtin_specs import MISSING, SPECS, bind_builtin
from bang.diagnostics import type_name
from bang.semantic.semantic_nodes import (
    ArrayType,
    BoolType,
    BuiltinType,
    DataClassType,
    DictType,
    DynamicType,
    FrozenSetType,
    FunctionType,
    NoneType,
    NumberType,
    SetType,
    StringType,
)


CALLABLES = (FunctionType, BuiltinType, DataClassType)
ITERABLES = (ArrayType, StringType, DictType, SetType, FrozenSetType)


def fact_kind(fact):
    if type(fact) is DynamicType:
        return "unknown"
    if type(fact) in CALLABLES:
        return "callable"
    if type(fact) in ITERABLES:
        return "iterable"
    return "other"


def known(fact, default=MISSING):
    value = getattr(fact, "value", None)
    return default if value is None else value


def set_contents(bound):
    if "transform" in bound.values:
        return None
    fact = bound.values.get("input", ArrayType([]))
    if type(fact) is StringType and fact.value is not None:
        items = [StringType(char) for char in fact.value]
    elif type(fact) in (ArrayType, SetType, FrozenSetType) and fact.value is not None:
        items = fact.value
    else:
        return None
    unique = {}
    for item in items:
        if type(item) not in (NumberType, BoolType, NoneType, StringType) or item.value is None:
            return None
        unique.setdefault(item.value, item)
    return list(unique.values())


def check_dict(checker, root, bound):
    options = bound.values
    items = list(bound.items)
    keys = None
    if "values" in options:
        key_fact = items[0] if len(items) == 1 else ArrayType(items)
        value_fact = options["values"]
        for role, fact in (("keys", key_fact), ("values", value_fact)):
            if type(fact) not in ITERABLES + (DynamicType,):
                checker._error(f"dict {role} must be iterable (got {type_name(fact)})", root)
        if type(key_fact) is ArrayType and type(value_fact) is ArrayType:
            if key_fact.value is not None and value_fact.value is not None:
                if len(key_fact.value) != len(value_fact.value):
                    checker._error(
                        f"dict keys/values length mismatch ({len(key_fact.value)} and "
                        f"{len(value_fact.value)})", root,
                    )
                keys = key_fact.value
    else:
        if len(items) == 1:
            fact = items[0]
            if type(fact) in (DynamicType, DictType):
                return
            if type(fact) in (SetType, FrozenSetType):
                if fact.value is not None and len(fact.value) % 2:
                    checker._error("dict requires a value for every key", root)
                return
            if type(fact) is not ArrayType:
                checker._error("dict needs key/value pairs, a mapping, or an array of pairs", root)
            if fact.value is None:
                return
            items = fact.value
        if items and all(type(item) is ArrayType for item in items):
            for index, item in enumerate(items):
                if item.value is None:
                    return
                if len(item.value) != 2:
                    checker._error(f"dict pair {index + 1} must contain exactly two values", root)
            keys = [item.value[0] for item in items]
        else:
            if len(items) % 2:
                checker._error("dict requires a value for every key", root)
            keys = items[::2]
    if keys is not None and any(type(key) in checker.UNHASHABLE_TYPES for key in keys):
        checker._error("dict requires hashable elements or keys", root)


def infer_builtin(checker, root, name, arguments):
    try:
        bound = bind_builtin(name, arguments, root.keyword_names, kind_of=fact_kind)
    except ValueError as error:
        checker._error(str(error), root)
    spec, options = SPECS[name], bound.values
    for flag in spec.booleans:
        if flag not in options:
            continue
        fact = options[flag]
        if type(fact) is DynamicType:
            continue
        value = known(fact)
        if type(fact) not in (NumberType, BoolType, NoneType) or (
            value is not MISSING and (type(value) not in (int, bool) or value not in (0, 1))
        ):
            checker._error(f"{name} option '{flag}' must be true or false (1 or 0)", root)
    for callback in spec.callbacks:
        if callback in options and not bound.uncertain_order:
            if type(options[callback]) not in CALLABLES + (DynamicType,):
                checker._error(f"{name} option '{callback}' must be callable", root)
    for option in ("sep", "end") if name == "print" else ():
        if option in options and type(options[option]) not in (StringType, DynamicType):
            checker._error("print options 'sep' and 'end' must be strings", root)
    if name == "input" and "input" in options:
        if type(options["input"]) not in (StringType, DynamicType):
            checker._error(
                f"input prompt must be a string (got {type_name(options['input'])})", root,
            )
    if name in ("sum", "set", "len", "map", "filter", "reduce"):
        value = options.get("input")
        if value is not None and not bound.uncertain_order:
            if type(value) not in ITERABLES + (DynamicType,):
                checker._error(f"{name} expects an iterable input (got {type_name(value)})", root)
    if name == "set" and "transform" not in options:
        value = options.get("input")
        if type(value) is ArrayType and value.value is not None:
            if any(type(item) in checker.UNHASHABLE_TYPES for item in value.value):
                checker._error("set requires hashable elements or keys", root)
    if name == "dict":
        check_dict(checker, root, bound)
    if name == "sort":
        in_place = known(options["in_place"]) if "in_place" in options else 0
        if in_place is MISSING or in_place:
            value = bound.items[0] if len(bound.items) == 1 else None
            if in_place == 1 and (value is None or type(value) not in (ArrayType, DynamicType)):
                checker._error("sort in_place=true requires one array input", root)
            if value is not None:
                checker._invalidate_mutable_facts([value])
    if name in ("map", "filter", "reduce") or any(key in options for key in spec.callbacks):
        checker._invalidate_call_facts()
    if name in ("print", "len", "int"):
        return NumberType(None)
    if name == "input":
        return StringType(None)
    if name in ("map", "filter", "sort", "range"):
        return ArrayType(None)
    if name == "dict":
        return DictType(None)
    if name == "set":
        frozen = known(options["frozen"]) if "frozen" in options else 0
        if frozen is MISSING:
            return DynamicType()
        contents = set_contents(bound)
        return FrozenSetType(contents) if frozen else SetType(contents)
    return DynamicType()
