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
    id: id
    name: str
    oak: str | None
    has_seen_popup: bool

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
    """
    maplist_cur: MaplistProfile
    maplist_all: MaplistProfile
    created_maps: list["src.db.models.maps.PartialMap"]
    completions: list[ListCompletion]

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
        }
        if with_completions:
            data["completions"] = [c.to_dict() for c in self.completions]
        return data
