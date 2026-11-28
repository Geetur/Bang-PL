"""Builtin interfaces shared by checking and execution. No values are evaluated here."""

from dataclasses import dataclass
from typing import Any


MISSING = object()


@dataclass(frozen=True, slots=True)
class BuiltinSpec:
    parameters: tuple[str, ...] = ("input",)
    required: tuple[str, ...] = ("input",)
    options: tuple[str, ...] = ()
    booleans: tuple[str, ...] = ()
    callbacks: tuple[str, ...] = ()
    aliases: tuple[tuple[str, str], ...] = ()
    variadic: bool = False


SPECS = {
    "print": BuiltinSpec(
        required=(), options=("sep", "end", "flush", "spread"),
        booleans=("flush", "spread"), variadic=True,
    ),
    "len": BuiltinSpec(options=("where",), callbacks=("where",)),
    "int": BuiltinSpec(options=("base",)),
    "input": BuiltinSpec(
        required=(), options=("strip",), booleans=("strip",), aliases=(("prompt", "input"),)
    ),
    "sum": BuiltinSpec(options=("initial", "transform"), callbacks=("transform",)),
    "set": BuiltinSpec(
        required=(), options=("frozen", "transform"), booleans=("frozen",),
        callbacks=("transform",),
    ),
    "dict": BuiltinSpec(
        required=(), options=("values", "strict"), booleans=("strict",), variadic=True,
    ),
    "min": BuiltinSpec(options=("key", "default"), callbacks=("key",), variadic=True),
    "max": BuiltinSpec(options=("key", "default"), callbacks=("key",), variadic=True),
    "sort": BuiltinSpec(
        options=("key", "reverse", "in_place"), booleans=("reverse", "in_place"),
        callbacks=("key",), variadic=True,
    ),
    "range": BuiltinSpec(
        required=(), options=("start", "step", "inclusive"), booleans=("inclusive",),
        aliases=(("stop", "input"),),
    ),
    "map": BuiltinSpec(
        parameters=("input", "transform"), required=("input", "transform"),
        options=("indexed",), booleans=("indexed",), callbacks=("transform",),
    ),
    "filter": BuiltinSpec(
        parameters=("input", "predicate"), required=("input", "predicate"),
        options=("indexed", "invert"), booleans=("indexed", "invert"), callbacks=("predicate",),
    ),
    "reduce": BuiltinSpec(
        parameters=("input", "combine", "initial"), required=("input", "combine"),
        options=("indexed",), booleans=("indexed",), callbacks=("combine",),
    ),
}


@dataclass(slots=True)
class BoundBuiltin:
    values: dict[str, Any]
    items: tuple[Any, ...] = ()
    uncertain_order: bool = False


def bind_builtin(name, arguments, keyword_names=(), *, kind_of=None):
    spec = SPECS[name]
    aliases = dict(spec.aliases)
    allowed = set(spec.parameters) | set(spec.options)
    supplied = {}
    positional = []
    named_seen = False
    labels = keyword_names or (None,) * len(arguments)
    for label, value in zip(labels, arguments, strict=True):
        if label is None:
            if named_seen:
                raise ValueError("positional arguments must precede named arguments")
            positional.append(value)
            continue
        named_seen = True
        original = label
        label = aliases.get(label, label)
        if label not in allowed:
            options = ", ".join(spec.parameters + spec.options)
            raise ValueError(f"{name} has no option '{original}'; allowed parameters: {options}")
        if label in supplied:
            raise ValueError(f"{name} received multiple values for '{label}'")
        supplied[label] = value

    uncertain = False
    if name in ("map", "filter", "reduce") and len(positional) >= 2 and "input" not in supplied:
        first = kind_of(positional[0]) if kind_of else "unknown"
        second = kind_of(positional[1]) if kind_of else "unknown"
        if first == "callable" and second == "iterable":
            positional[:2] = positional[1], positional[0]
        elif first in ("callable", "unknown") and second in ("iterable", "unknown"):
            uncertain = True

    if spec.variadic:
        if positional and "input" in supplied:
            raise ValueError(f"{name} received multiple values for 'input'")
        items = tuple(positional) if positional else (
            (supplied["input"],) if "input" in supplied else ()
        )
        if len(positional) == 1:
            supplied["input"] = positional[0]
    else:
        parameters = spec.parameters
        if name == "range" and len(positional) > 1:
            parameters = ("start", "input", "step")
        if len(positional) > len(parameters):
            if name in ("sum", "set"):
                raise ValueError(f"{name} expects one iterable input; put the values in an array")
            raise ValueError(
                f"{name} received too many positional arguments "
                f"(expected at most {len(parameters)}, got {len(positional)})"
            )
        for parameter, value in zip(parameters, positional, strict=False):
            if parameter in supplied:
                raise ValueError(f"{name} received multiple values for '{parameter}'")
            supplied[parameter] = value
        items = ()

    for parameter in spec.required:
        present = parameter in supplied or (parameter == "input" and spec.variadic and bool(items))
        if not present:
            raise ValueError(f"{name} is missing required argument '{parameter}'")
    return BoundBuiltin(supplied, items, uncertain)
