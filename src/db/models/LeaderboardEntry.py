from dataclasses import dataclass


@dataclass
class LeaderboardEntry:
    """
    type: object
    properties:
      user_id:
        $ref: "#/components/schemas/DiscordID"
      score:
        type: number
        description: The user's score
      position:
        type: integer
        description: Position on the list.
    """
    user_id: int
    score: float
    position: int

    def to_dict(self) -> dict:
        return {
            "user_id": str(self.user_id),
            "score": self.score,
            "position": self.position,
        }
