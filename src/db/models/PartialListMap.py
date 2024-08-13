from dataclasses import dataclass


@dataclass
class PartialListMap:
    name: str
    code: str
    placement: int
    verified: bool

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "code": self.code,
            "placement": self.placement,
            "verified": self.verified,
        }
