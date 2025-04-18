from dataclasses import dataclass
from typing import Any


@dataclass
class Config:
    """
    type: object
    properties:
      value:
        description: The actual value of the config var.
      formats:
        type: integer
        description: The formats that this config var belongs in.
      type:
        type: string
        description: The formats that this config var belongs in.
        enum: [int, float]
      description:
        type: string
        description: A human-readable version of the variable.
        enum: [int, float]
    """
    value: Any
    formats: list[int]
    type: str
    description: str

    def to_dict(self) -> dict:
        return {
            "value": self.value,
            "formats": self.formats,
            "type": self.type,
            "description": self.description,
        }
