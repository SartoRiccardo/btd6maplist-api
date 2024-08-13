from dataclasses import dataclass


@dataclass
class User:
    id: id
    name: str
    oak: str

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
        }
