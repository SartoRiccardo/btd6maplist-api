from dataclasses import dataclass
from .challenges import ListCompletion


@dataclass
class PartialUser:
    """
    type: object
    properties:
      id:
        type: string
        description: The user's Discord ID.
      name:
        type: string
        description: The user's name.
    ---
    Profile:
      allOf:
      - $ref: "#/components/schemas/PartialUser"
      - type: object
        properties:
          oak:
            type: string
            nullable: true
            description: The user's NinjaKiwi OpenData Access Key
          has_seen_popup:
            type: boolean
            description: |
              Whether the user has already been notified there are rules
              to submissions.
    """
    id: int
    name: str
    oak: str | None
    has_seen_popup: bool

    def __eq__(self, other):
        if isinstance(other, PartialUser):
            return self.id == other.id and self.name == other.name
        return NotImplemented

    def __hash__(self):
        return hash(f"{self.id}//{self.name}")

    def to_dict(self, profile: bool = False) -> dict:
        extra_fields = {}
        if profile:
            extra_fields = {
                "oak": self.oak,
                "has_seen_popup": self.has_seen_popup,
            }
        return {
            "id": str(self.id),
            "name": self.name,
            **extra_fields,
        }


@dataclass
class MaplistProfile:
    """
    type: object
    properties:
      points:
        type: integer
        description: Points on the leaderboard.
      pts_placement:
        type: integer
        nullable: true
        description: Placement on the points leaderboard.
      lccs:
        type: integer
        description: Number of current LCCs.
      lccs_placement:
        type: integer
        nullable: true
        description: Placement on the LCC leaderboard.
    """
    points: int
    pts_placement: int
    lccs: int
    lccs_placement: int

    def to_dict(self) -> dict:
        return {
            "points": self.points,
            "pts_placement": self.pts_placement,
            "lccs": self.lccs,
            "lccs_placement": self.lccs_placement,
        }


@dataclass
class MaplistMedals:
    """
    type: object
    properties:
      wins:
        type: integer
        description: Number of completions.
      black_border:
        type: integer
        description: Number of black border completions.
      no_geraldo:
        type: integer
        description: Number of No Optimal Hero completions.
      lccs:
        type: integer
        description: Number of LCCs.
    """
    wins: int
    black_border: int
    no_geraldo: int
    lccs: int

    def to_dict(self) -> dict:
        return {
            "wins": self.wins,
            "black_border": self.black_border,
            "no_geraldo": self.no_geraldo,
            "lccs": self.lccs,
        }


@dataclass
class User(PartialUser):
    """
    allOf:
    - $ref: "#/components/schemas/PartialUser"
    - type: object
      properties:
        maplist_cur:
          $ref: "#/components/schemas/MaplistProfile"
        maplist_all:
          $ref: "#/components/schemas/MaplistProfile"
        created_maps:
          type: array
          items:
            $ref: "#/components/schemas/PartialMap"
        medals:
          $ref: "#/components/schemas/MaplistMedals"
    """
    maplist_cur: MaplistProfile
    maplist_all: MaplistProfile
    created_maps: list["src.db.models.maps.PartialMap"]
    completions: list[ListCompletion]
    medals: MaplistMedals

    def to_dict(
            self,
            profile: bool = False,
            with_completions: bool = False
    ) -> dict:
        data = {
            **super().to_dict(profile=profile),
            "maplist": {
                "current": self.maplist_cur.to_dict(),
                "all": self.maplist_all.to_dict(),
            },
            "created_maps": [m.to_dict() for m in self.created_maps],
            "medals": self.medals.to_dict(),
        }
        if with_completions:
            data["completions"] = [c.to_dict() for c in self.completions]
        return data
