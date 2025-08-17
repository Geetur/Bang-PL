from dataclasses import dataclass

from bang.parsing.parser_nodes import BlockNode


# add repr instead of changing print
@dataclass
class runtime_function:
    body: BlockNode
    params_name: str
    closure: list


@dataclass
class runtime_dataclass:
    fields: list[str]


@dataclass
class runtime_instance:
    of: runtime_dataclass
    fields: dict  # field_name -> value

    def __repr__(self):
        inner = ", ".join(f"{k}={repr(v)}" for k, v in self.fields.items())
        return f"{self.of.name}{{{inner}}}"
