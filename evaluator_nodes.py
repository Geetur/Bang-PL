from dataclasses import dataclass
from typing import Any, List, Optional
from parser_nodes import (
    BlockNode
)
@dataclass
class runtime_function:
    body: BlockNode
    params_name: str
    closure: list


