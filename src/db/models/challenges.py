from dataclasses import dataclass


@dataclass
class LCC:
    id: int
    leftover: int
    proof: str
    players: list[int]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "leftover": self.leftover,
            "proof": self.proof,
            "players": [str(p) for p in self.players],
        }


@dataclass
class ListCompletion:
    map: str
    user_id: int
    black_border: bool
    no_geraldo: bool
    current_lcc: bool

    def to_dict(self) -> dict:
        return {
            "map": self.map,
            "user_id": str(self.user_id),
            "black_border": self.black_border,
            "no_geraldo": self.no_geraldo,
            "current_lcc": self.current_lcc,
        }
