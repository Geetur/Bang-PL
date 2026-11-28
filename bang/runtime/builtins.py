"""Input-oriented builtins. Binding is shared with the semantic checker."""

import builtins
from functools import partial

from bang.builtin_specs import MISSING, SPECS
from bang.diagnostics import type_name
from bang.lexing.lexer_tokens import T_PLUS_ENUM_VAL
from bang.parsing.parser_nodes import BinOpNode
from bang.runtime.evaluator_nodes import (
    RUN_TIME_BUILTIN,
    RUN_TIME_DATACLASS,
    RUN_TIME_FUNCTION,
    format_value,
)

ITERABLE_TYPES = (list, str, dict, set, frozenset)
CALLABLE_TYPES = (RUN_TIME_FUNCTION, RUN_TIME_BUILTIN, RUN_TIME_DATACLASS)


def runtime_kind(value):
    if type(value) in CALLABLE_TYPES:
        return "callable"
    if type(value) in ITERABLE_TYPES:
        return "iterable"
    return "other"


def build_builtins(evaluator):
    library = BuiltinLibrary(evaluator)
    return {name: RUN_TIME_BUILTIN(name, partial(library.invoke, name)) for name in SPECS}


class BuiltinLibrary:
    def __init__(self, evaluator):
        self.evaluator = evaluator

    def fail(self, message, metadata):
        self.evaluator._error(message, metadata)

    def invoke(self, name, bound, metadata):
        for flag in SPECS[name].booleans:
            if flag in bound.values:
                value = bound.values[flag]
                if type(value) not in (int, bool) or value not in (0, 1):
                    self.fail(f"{name} option '{flag}' must be true or false (1 or 0)", metadata)
        for option in SPECS[name].callbacks:
            if option in bound.values and type(bound.values[option]) not in CALLABLE_TYPES:
                self.fail(f"{name} option '{option}' must be callable", metadata)
        return getattr(self, "do_" + name)(bound, metadata)

    def call(self, callback, arguments, metadata):
        return self.evaluator._invoke_callable(callback, arguments, metadata)

    def iterable(self, name, value, metadata):
        if type(value) not in ITERABLE_TYPES:
            self.fail(f"{name} expects an iterable input (got {type_name(value)})", metadata)
        return list(value)

    def aggregate(self, name, bound, metadata):
        if len(bound.items) > 1:
            return list(bound.items)
        value = bound.items[0]
        if type(value) in ITERABLE_TYPES:
            return list(value)
        return [value]  # Retain the old single-scalar min/max/sort forms.

    def do_print(self, bound, metadata):
        options = bound.values
        sep, ending = options.get("sep", " "), options.get("end", "\n")
        if type(sep) is not str or type(ending) is not str:
            self.fail("print options 'sep' and 'end' must be strings", metadata)
        values = list(bound.items)
        if options.get("spread", 0) and values:
            if len(values) != 1:
                self.fail("print with spread=true needs one iterable input", metadata)
            values = self.iterable("print", values[0], metadata)
        builtins.print(
            *(format_value(value) for value in values),
            sep=sep,
            end=ending,
            flush=bool(options.get("flush", 0)),
        )
        return 0

    def do_len(self, bound, metadata):
        value = bound.values["input"]
        if type(value) not in ITERABLE_TYPES:
            self.fail(f"len expects an iterable input (got {type_name(value)})", metadata)
        where = bound.values.get("where", MISSING)
        if where is MISSING:
            return len(value)
        return sum(bool(self.call(where, [item], metadata)) for item in list(value))

    def do_int(self, bound, metadata):
        value, base = bound.values["input"], bound.values.get("base", 10)
        if type(base) not in (int, bool) or base != 0 and not 2 <= base <= 36:
            self.fail("int base must be 0 or an integer from 2 through 36", metadata)
        if isinstance(value, int | float):
            if base != 10:
                self.fail("int bases other than 10 require a string input", metadata)
            return int(value)
        if type(value) is not str:
            self.fail(f"int expects a number or integer string (got {type_name(value)})", metadata)
        text = value.strip()
        digits = text[1:] if text.startswith(("+", "-")) else text
        prefix_base = {"0x": 16, "0o": 8, "0b": 2}.get(digits[:2].lower())
        if prefix_base is not None and base in (0, prefix_base):
            digits = digits[2:]
        if not digits or not text.isascii() or "_" in text:
            self.fail("int expects an ASCII integer string in the requested base", metadata)
        if len(digits) > 4300:
            self.fail("int string exceeds the limit of 4300 digits", metadata)
        try:
            return int(text, base)
        except ValueError:
            self.fail(f"int input is not a valid base-{base} integer string", metadata)

    def do_input(self, bound, metadata):
        prompt = bound.values.get("input", "")
        if type(prompt) is not str:
            self.fail(f"input prompt must be a string (got {type_name(prompt)})", metadata)
        try:
            value = builtins.input(prompt)
        except EOFError:
            self.fail("input reached end of input", metadata)
        except OSError as error:
            self.fail(f"input could not read standard input: {error}", metadata)
        return value.strip() if bound.values.get("strip", 0) else value

    def do_sum(self, bound, metadata):
        values = self.iterable("sum", bound.values["input"], metadata)
        transform = bound.values.get("transform", MISSING)
        accumulator = bound.values.get("initial", MISSING)
        operation = BinOpNode(None, T_PLUS_ENUM_VAL, metadata, None)
        for value in values:
            if transform is not MISSING:
                value = self.call(transform, [value], metadata)
            if accumulator is MISSING:
                factories = {
                    int: int,
                    float: int,
                    bool: int,
                    str: str,
                    list: list,
                    set: set,
                    frozenset: frozenset,
                    dict: dict,
                }
                factory = factories.get(type(value))
                if factory is None:
                    self.fail(
                        "sum items need a supported '+' operation or an initial value",
                        metadata,
                    )
                accumulator = factory()
            accumulator = self.evaluator._eval_binary_values(operation, accumulator, value)
        return 0 if accumulator is MISSING else accumulator

    def do_set(self, bound, metadata):
        values = self.iterable("set", bound.values.get("input", []), metadata)
        transform = bound.values.get("transform", MISSING)
        result = set()
        for index, value in enumerate(values):
            if transform is not MISSING:
                value = self.call(transform, [value], metadata)
            try:
                result.add(value)
            except TypeError:
                self.fail(
                    f"set item {index + 1} must be hashable (got {type_name(value)})",
                    metadata,
                )
        return frozenset(result) if bound.values.get("frozen", 0) else result

    def do_dict(self, bound, metadata):
        options = bound.values
        raw = (
            []
            if not bound.items
            else (bound.items[0] if len(bound.items) == 1 else list(bound.items))
        )
        if "values" in options:
            keys = self.iterable("dict keys", raw, metadata)
            values = self.iterable("dict values", options["values"], metadata)
            if len(keys) != len(values):
                self.fail(
                    f"dict keys/values length mismatch ({len(keys)} and {len(values)})",
                    metadata,
                )
            pairs = list(zip(keys, values, strict=True))
        elif type(raw) is dict:
            pairs = list(raw.items())
        else:
            if type(raw) not in (list, set, frozenset):
                self.fail("dict needs key/value pairs, a mapping, or an array of pairs", metadata)
            items = list(raw)
            if items and all(type(item) is list for item in items):
                for index, item in enumerate(items):
                    if len(item) != 2:
                        self.fail(
                            f"dict pair {index + 1} must contain exactly two values",
                            metadata,
                        )
                pairs = items
            else:
                if len(items) % 2:
                    self.fail("dict requires a value for every key", metadata)
                pairs = list(zip(items[::2], items[1::2], strict=True))
        result = {}
        for index, (key, value) in enumerate(pairs):
            try:
                if options.get("strict", 0) and key in result:
                    self.fail(f"dict received a duplicate key at pair {index + 1}", metadata)
                result[key] = value
            except TypeError:
                self.fail(f"dict key {index + 1} must be hashable (got {type_name(key)})", metadata)
        return result

    def extrema(self, name, bound, metadata):
        values = self.aggregate(name, bound, metadata)
        if not values:
            if "default" in bound.values:
                return bound.values["default"]
            self.fail(f"{name} needs a nonempty input or a default value", metadata)
        key = bound.values.get("key", MISSING)
        selected = values[0]
        selected_key = selected if key is MISSING else self.call(key, [selected], metadata)
        for value in values[1:]:
            candidate = value if key is MISSING else self.call(key, [value], metadata)
            try:
                better = candidate < selected_key if name == "min" else candidate > selected_key
            except (TypeError, RecursionError):
                self.fail(
                    f"{name} expects comparable key values "
                    f"(got {type_name(selected_key)} and {type_name(candidate)})",
                    metadata,
                )
            if better:
                selected, selected_key = value, candidate
        return selected

    def do_min(self, bound, metadata):
        return self.extrema("min", bound, metadata)

    def do_max(self, bound, metadata):
        return self.extrema("max", bound, metadata)

    def do_sort(self, bound, metadata):
        options = bound.values
        original = bound.items[0] if len(bound.items) == 1 else MISSING
        if options.get("in_place", 0) and type(original) is not list:
            self.fail("sort in_place=true requires one array input", metadata)
        values = self.aggregate("sort", bound, metadata)
        key = options.get("key", MISSING)
        key_function = None if key is MISSING else lambda value: self.call(key, [value], metadata)
        try:
            result = sorted(values, key=key_function, reverse=bool(options.get("reverse", 0)))
        except (TypeError, RecursionError):
            self.fail("sort expects mutually comparable key values", metadata)
        if options.get("in_place", 0):
            original[:] = result
            return original
        return result

    def do_range(self, bound, metadata):
        options = dict(bound.values)
        stop = options.pop("input", 0)
        if type(stop) is list:
            if len(stop) > 3:
                self.fail("range input array accepts at most three values", metadata)
            if len(stop) > 1:
                if "start" in options:
                    self.fail("range received multiple values for 'start'", metadata)
                options["start"] = stop[0]
            if len(stop) > 2:
                if "step" in options:
                    self.fail("range received multiple values for 'step'", metadata)
                options["step"] = stop[2]
            stop = stop[1] if len(stop) > 1 else stop[0] if stop else 0
        start, step = options.get("start", 0), options.get("step", 1)
        if any(type(value) not in (int, bool) for value in (start, stop, step)):
            self.fail("range start, stop, and step must be integers", metadata)
        if step == 0:
            self.fail("range step cannot be zero", metadata)
        if options.get("inclusive", 0):
            stop += 1 if step > 0 else -1
        return list(range(start, stop, step))

    def functional(self, name, bound, metadata):
        values = self.iterable(name, bound.values["input"], metadata)
        callback_name = {"map": "transform", "filter": "predicate", "reduce": "combine"}[name]
        callback = bound.values[callback_name]
        indexed = bound.values.get("indexed", 0)
        if name == "reduce":
            if "initial" in bound.values:
                accumulator, start = bound.values["initial"], 0
            elif values:
                accumulator, start = values[0], 1
            else:
                self.fail("reduce needs an initial value when the input is empty", metadata)
            for index in range(start, len(values)):
                arguments = [accumulator, values[index]] + ([index] if indexed else [])
                accumulator = self.call(callback, arguments, metadata)
            return accumulator
        result = []
        for index, value in enumerate(values):
            arguments = [value] + ([index] if indexed else [])
            returned = self.call(callback, arguments, metadata)
            if name == "map":
                result.append(returned)
            elif bool(returned) != bool(bound.values.get("invert", 0)):
                result.append(value)
        return result

    def do_map(self, bound, metadata):
        return self.functional("map", bound, metadata)

    def do_filter(self, bound, metadata):
        return self.functional("filter", bound, metadata)

    def do_reduce(self, bound, metadata):
        return self.functional("reduce", bound, metadata)

    def do_enumerate(self, bound, metadata):
        start = bound.values.get("start", 0)
        if type(start) not in (int, bool):
            self.fail("enumerate start must be an integer", metadata)
        values = self.iterable("enumerate", bound.values["input"], metadata)
        return [[index, value] for index, value in enumerate(values, start)]

    def do_zip(self, bound, metadata):
        sources = bound.values["input"]
        if type(sources) is not list:
            self.fail("zip expects an array of iterable inputs", metadata)
        columns = [
            self.iterable(f"zip input {i + 1}", value, metadata)
            for i, value in enumerate(list(sources))
        ]
        if bound.values.get("strict", 1) and len({len(value) for value in columns}) > 1:
            self.fail("zip inputs must have equal lengths when strict=true", metadata)
        return [list(row) for row in zip(*columns, strict=False)]

    def quantify(self, name, bound, metadata):
        values = self.iterable(name, bound.values["input"], metadata)
        predicate = bound.values.get("predicate", MISSING)
        for value in values:
            result = value if predicate is MISSING else self.call(predicate, [value], metadata)
            if bool(result) == (name == "any"):
                return int(name == "any")
        return int(name == "all")

    def do_any(self, bound, metadata):
        return self.quantify("any", bound, metadata)

    def do_all(self, bound, metadata):
        return self.quantify("all", bound, metadata)

    def mapping(self, name, value, metadata):
        if type(value) is not dict:
            self.fail(f"{name} expects a dictionary input (got {type_name(value)})", metadata)
        return value

    def do_items(self, bound, metadata):
        mapping = self.mapping("items", bound.values["input"], metadata)
        return [[key, value] for key, value in list(mapping.items())]

    def do_get(self, bound, metadata):
        mapping = self.mapping("get", bound.values["input"], metadata)
        key = bound.values["key"]
        try:
            return mapping.get(key, bound.values.get("default", 0))
        except TypeError:
            self.fail(f"get key must be hashable (got {type_name(key)})", metadata)

    def do_array(self, bound, metadata):
        return self.iterable("array", bound.values.get("input", []), metadata)

    def do_str(self, bound, metadata):
        return format_value(bound.values["input"])

    def do_float(self, bound, metadata):
        value = bound.values["input"]
        if type(value) not in (str, int, bool, float):
            self.fail(
                f"float expects a number or numeric string (got {type_name(value)})",
                metadata,
            )
        if type(value) is str:
            value = value.strip()
            if not value or not value.isascii() or "_" in value:
                self.fail("float expects an ASCII numeric string without underscores", metadata)
            if sum(char.isdigit() for char in value) > 4300:
                self.fail("float string exceeds the limit of 4300 digits", metadata)
        try:
            return self.evaluator._checked_real_result(float(value))
        except (ValueError, OverflowError) as error:
            self.fail(f"float expects a finite numeric value: {error}", metadata)

    def do_join(self, bound, metadata):
        separator = bound.values.get("sep", "")
        if type(separator) is not str:
            self.fail("join option 'sep' must be a string", metadata)
        values = self.iterable("join", bound.values["input"], metadata)
        for index, value in enumerate(values):
            if type(value) is not str:
                self.fail(
                    f"join item {index + 1} must be a string (got {type_name(value)})",
                    metadata,
                )
        return separator.join(values)

    def do_assert(self, bound, metadata):
        message = bound.values.get("message", "assertion failed")
        if type(message) is not str:
            self.fail("assert option 'message' must be a string", metadata)
        if not bound.values["input"]:
            self.fail(
                "assertion failed" + (": " + message if "message" in bound.values else ""),
                metadata,
            )
        return 0

    def group(self, name, bound, metadata):
        values = self.iterable(name, bound.values["input"], metadata)
        callback = bound.values.get("key", MISSING)
        result = {}
        for index, value in enumerate(values):
            key = value if callback is MISSING else self.call(callback, [value], metadata)
            try:
                if name == "counts":
                    result[key] = result.get(key, 0) + 1
                else:
                    result.setdefault(key, []).append(value)
            except TypeError:
                self.fail(
                    f"{name} key for item {index + 1} must be hashable (got {type_name(key)})",
                    metadata,
                )
        return result

    def do_counts(self, bound, metadata):
        return self.group("counts", bound, metadata)

    def do_group_by(self, bound, metadata):
        return self.group("group_by", bound, metadata)

    def do_read(self, bound, metadata):
        path = bound.values["input"]
        if type(path) is not str:
            self.fail("read path must be a string", metadata)
        try:
            with builtins.open(path, "rb") as stream:
                text = stream.read().decode("utf-8")
        except (OSError, ValueError) as error:
            self.fail(f"read could not read UTF-8 file {path!r}: {error}", metadata)
        if not bound.values.get("lines", 0):
            return text
        lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        if lines[-1] == "":
            lines.pop()
        return lines

    def do_write(self, bound, metadata):
        text, path = bound.values["input"], bound.values["path"]
        if type(text) is not str or type(path) is not str:
            self.fail("write input and path must be strings", metadata)
        try:
            data = text.encode("utf-8")
            with builtins.open(path, "ab" if bound.values.get("append", 0) else "wb") as stream:
                return stream.write(data)
        except (OSError, ValueError) as error:
            self.fail(f"write could not write UTF-8 file {path!r}: {error}", metadata)
