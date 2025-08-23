from dataclasses import dataclass

from bang.parsing.parser_nodes import BlockNode


@dataclass
class runtime_function:
    body: BlockNode
    params_name: str
    closure: list

    def repr(self) -> str:
        return f"<fn {id(self)}>"


@dataclass
class runtime_dataclass:
    fields: list[str]

    def repr(self) -> str:
        return f"<data {id(self)}>"


@dataclass
class runtime_instance:
    of: str
    fields: dict  # field_name -> value

    def __repr__(self) -> str:
        return f"<instance {id(self)}>"
