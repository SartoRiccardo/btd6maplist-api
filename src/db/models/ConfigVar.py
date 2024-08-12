from dataclasses import dataclass
from typing import Any


@dataclass
class ConfigVar:
    name: str
    value: Any

    def to_dict(self):
        return {
            "name": self.name,
            "value": self.value,
        }
