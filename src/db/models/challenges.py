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
            "players": self.players,
        }
