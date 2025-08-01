from dataclasses import dataclass
from typing import Any

from bang.parsing.parser_nodes import BlockNode


@dataclass
class NumberType:
    value: int


@dataclass
class BoolType:
    value: bool


@dataclass
class StringType:
    value: str


@dataclass
class NoneType:
    value: None


@dataclass
class ArrayType:
    value: list[Any]


@dataclass
class CallListType:
    value: list[Any]


@dataclass
class DynamicType:
    value: None = None


@dataclass
class IdentifierType:
    value: Any


@dataclass
class FunctionType:
    value: BlockNode
