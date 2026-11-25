from dataclasses import dataclass

from bang.parsing.parser_nodes import BlockNode


@dataclass(slots=True, eq=False)
class runtime_function:
    body: BlockNode
    params_name: str
    closure: list

    def __deepcopy__(self, memo):
        return self

    def __repr__(self) -> str:
        return f"<fn {id(self)}>"


@dataclass(slots=True, eq=False)
class runtime_dataclass:
    fields: tuple[str, ...]
    name: str = "<data>"

    def __deepcopy__(self, memo):
        return self

    def __repr__(self) -> str:
        return f"<data {id(self)}>"


@dataclass(slots=True, eq=False)
class runtime_instance:
    of: runtime_dataclass
    fields: dict  # field_name -> value

    def __repr__(self) -> str:
        return f"<instance {id(self)}>"


RUN_TIME_INSTANCE = runtime_instance
RUN_TIME_DATACLASS = runtime_dataclass
RUN_TIME_FUNCTION = runtime_function
