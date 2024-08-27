from dataclasses import dataclass
from typing import Any


@dataclass
class ConfigVar:
    """
    type: object
    properties:
      name:
        type: string
        description: The name of the variable
      value:
        description: The value of the variable. Can be of any type.
    """
    name: str
    value: Any

    def to_dict(self):
        return {
            "name": self.name,
            "value": self.value,
        }
