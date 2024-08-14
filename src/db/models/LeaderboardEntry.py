from dataclasses import dataclass


@dataclass
class LeaderboardEntry:
    user_id: int
    score: float
    position: int

    def to_dict(self) -> dict:
        return {
            "user_id": str(self.user_id),
            "score": self.score,
            "position": self.position,
        }
