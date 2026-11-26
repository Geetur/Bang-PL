from dataclasses import dataclass
from typing import Any


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


@dataclass(frozen=True, slots=True, eq=False)
class FunctionType:
    value: Any = None
    parameters: tuple[tuple[str, bool], ...] | None = None
    variadic_name: str | None = None

    def __deepcopy__(self, memo):
        return self


@dataclass(frozen=True, slots=True)
class BuiltinType:
    name: str

    def __deepcopy__(self, memo):
        return self


@dataclass(slots=True)
class SetType:
    value: Any


@dataclass(slots=True)
class DictType:
    value: Any


@dataclass(frozen=True, slots=True, eq=False)
class DataClassType:
    fields: tuple[str, ...]

    def __deepcopy__(self, memo):
        return self


@dataclass(slots=True)
class InstanceType:
    of: DataClassType
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
