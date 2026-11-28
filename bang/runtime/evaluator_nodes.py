from collections.abc import Callable
from dataclasses import dataclass

from bang.parsing.parser_nodes import BlockNode, ParameterNode


@dataclass(slots=True, eq=False)
class runtime_function:
    body: BlockNode
    params_name: str | None
    closure: list
    parameters: tuple[ParameterNode, ...] | None = None
    name: str | None = None
    line: int = 1

    def __deepcopy__(self, memo):
        return self

    def __repr__(self) -> str:
        return format_value(self)


@dataclass(slots=True, eq=False)
class runtime_builtin:
    name: str
    implementation: Callable[..., object]

    def __call__(self, args, metadata):
        return self.implementation(args, metadata)

    def __deepcopy__(self, memo):
        return self

    def __repr__(self) -> str:
        return format_value(self)


@dataclass(slots=True, eq=False)
class runtime_dataclass:
    fields: tuple[str, ...]
    name: str = "<data>"

    def __deepcopy__(self, memo):
        return self

    def __repr__(self) -> str:
        return format_value(self)


@dataclass(slots=True, eq=False)
class runtime_instance:
    of: runtime_dataclass
    fields: dict  # field_name -> value

    def __repr__(self) -> str:
        return format_value(self)


def format_value(value):
    """Format Bang values without exposing Python objects or recursing on cycles.

    Top-level strings are output verbatim; strings inside data are quoted.
    The active path distinguishes cycles from ordinary shared references.
    """
    output = []
    active = set()
    tasks = [("value", value, False)]
    while tasks:
        action, current, quoted = tasks.pop()
        if action == "text":
            output.append(current)
            continue
        if action == "leave":
            active.remove(current)
            continue
        typ = type(current)
        if typ is str:
            output.append(repr(current) if quoted else current)
        elif typ in (int, float, bool):
            output.append(str(current))
        elif current is None:
            output.append("none")
        elif typ is runtime_function:
            output.append(
                f"<fn {current.name}>"
                if current.name is not None
                else f"<anonymous fn at line {current.line}>"
            )
        elif typ is runtime_builtin:
            output.append(f"<builtin {current.name}>")
        elif typ is runtime_dataclass:
            output.append(f"<data {current.name} [{', '.join(current.fields)}]>")
        elif typ in (list, dict, set, runtime_instance):
            identity = id(current)
            if typ is list:
                opening, closing, cycle = "[", "]", "[...]"
            elif typ is runtime_instance:
                opening, closing = current.of.name + "{", "}"
                cycle = opening + "...}"
            elif typ is set and not current:
                output.append("set()")
                continue
            else:
                opening, closing, cycle = "{", "}", "{...}"
            if identity in active:
                output.append(cycle)
                continue
            active.add(identity)
            output.append(opening)
            contents = []
            if typ in (dict, runtime_instance):
                fields = current.fields if typ is runtime_instance else current
                for position, (key, item) in enumerate(fields.items()):
                    if position:
                        contents.append(("text", ", ", False))
                    if typ is runtime_instance:
                        contents.append(("text", key + "=", False))
                    else:
                        contents.extend((("value", key, True), ("text", ": ", False)))
                    contents.append(("value", item, True))
            else:
                for position, item in enumerate(current):
                    if position:
                        contents.append(("text", ", ", False))
                    contents.append(("value", item, True))
            tasks.extend((("leave", identity, False), ("text", closing, False)))
            tasks.extend(reversed(contents))
        else:
            output.append(f"<{typ.__name__}>")
    return "".join(output)


RUN_TIME_INSTANCE = runtime_instance
RUN_TIME_DATACLASS = runtime_dataclass
RUN_TIME_FUNCTION = runtime_function
RUN_TIME_BUILTIN = runtime_builtin
