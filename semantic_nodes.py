
from dataclasses import dataclass
from typing import Any, List, Optional
from parser_nodes import (
    BlockNode
)

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
    value: List[Any]

@dataclass
class CallListType:
    value: List[Any]
@dataclass
class DynamicType:
    value: None = None

@dataclass
class IdentifierType:
    value: Any

@dataclass
class FunctionType:
    value: BlockNode
    



