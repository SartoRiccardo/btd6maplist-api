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
    """
    id: id
    name: str
    oak: str

    def to_dict(self, with_oak: bool = False) -> dict:
        oak = {} if with_oak else {"oak": self.oak}
        return {
            "id": str(self.id),
            "name": self.name,
            **oak,
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
    completions: list[ListCompletion]
    created_maps: list["src.db.models.maps.PartialMap"]

    def to_dict(self, with_oak: bool = False) -> dict:
        return {
            **super().to_dict(),
            "maplist": {
                "current": self.maplist_cur.to_dict(),
                "all": self.maplist_all.to_dict(),
            },
            "completions": [c.to_dict() for c in self.completions],
            "created_maps": [m.to_dict() for m in self.created_maps],
        }
