from dataclasses import dataclass


@dataclass
class LeaderboardEntry:
    """
    type: object
    properties:
      user:
        $ref: "#/components/schemas/PartialUser"
      score:
        type: number
        description: The user's score
      position:
        type: integer
        description: Position on the list.
    """
    user: "src.db.models.PartialUser"
    score: float
    position: int

    def to_dict(self) -> dict:
        return {
            "user": self.user.to_dict(),
            "score": self.score,
            "position": self.position,
        }
