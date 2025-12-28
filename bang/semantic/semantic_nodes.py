from dataclasses import dataclass
from typing import Any

from bang.parsing.parser_nodes import BlockNode


@dataclass(slots=True)
class NumberType:
    value: int


@dataclass(slots=True)
class BoolType:
    value: bool


@dataclass(slots=True)
class StringType:
    value: str


@dataclass(slots=True)
class NoneType:
    value: None


@dataclass(slots=True)
class ArrayType:
    value: list[Any]


@dataclass(slots=True)
class CallListType:
    value: list[Any]


@dataclass(slots=True)
class DynamicType:
    value: None = None


@dataclass(slots=True)
class IdentifierType:
    value: Any


@dataclass(slots=True)
class FunctionType:
    value: BlockNode


@dataclass(slots=True)
class SetType:
    value: Any


@dataclass(slots=True)
class DictType:
    value: Any


@dataclass(slots=True)
class DataClassType:
    fields: list[str]


@dataclass(slots=True)
class InstanceType:
    of: str  # dataclass name
    fields: dict[str, Any]


ARRAY_TYPE_CLASS = ArrayType
BOOL_TYPE_CLASS = BoolType
DATA_CLASS_TYPE_CLASS = DataClassType
DICT_TYPE_CLASS = DictType
DYNAMIC_TYPE_CLASS = DynamicType
FUNCTION_TYPE_CLASS = FunctionType
INSTANCE_TYPE_CLASS = InstanceType
NONE_TYPE_CLASS = NoneType
NUMBER_TYPE_CLASS = NumberType
SET_TYPE_CLASS = SetType
STRING_TYPE_CLASS = StringType
