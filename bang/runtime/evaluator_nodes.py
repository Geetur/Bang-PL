from dataclasses import dataclass

from bang.parsing.parser_nodes import BlockNode


# add repr instead of changing print
@dataclass
class runtime_function:
    body: BlockNode
    params_name: str
    closure: list

    def __repr__(self) -> str:
        return f"<fn {id(self)}>"


@dataclass
class runtime_dataclass:
    fields: list[str]

    def __repr__(self) -> str:
        return f"<data {id(self)}>"


@dataclass
class runtime_instance:
    of: str
    fields: dict  # field_name -> value

    def __repr__(self) -> str:
        return f"<instance {id(self)}>"
