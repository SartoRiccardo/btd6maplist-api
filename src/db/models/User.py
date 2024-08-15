from dataclasses import dataclass
from .challenges import ListCompletion


@dataclass
class PartialUser:
    id: id
    name: str
    oak: str

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
        }


@dataclass
class MaplistProfile:
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
    maplist_cur: MaplistProfile
    maplist_all: MaplistProfile
    completions: list[ListCompletion]
    created_maps: list["src.db.models.maps.PartialMap"]

    def to_dict(self) -> dict:
        return {
            **super().to_dict(),
            "maplist": {
                "current": self.maplist_cur.to_dict(),
                "all": self.maplist_all.to_dict(),
            },
            "completions": [c.to_dict() for c in self.completions],
            "created_maps": [m.to_dict() for m in self.created_maps],
        }
