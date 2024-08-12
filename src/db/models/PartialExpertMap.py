from dataclasses import dataclass


@dataclass
class PartialExpertMap:
    name: str
    code: str
    difficulty: int

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "code": self.code,
            "difficulty": self.difficulty,
        }
