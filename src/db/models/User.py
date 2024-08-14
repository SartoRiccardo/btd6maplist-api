from dataclasses import dataclass
from .maps import PartialMap


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
    lcc_count: int
    cur_points: int
    cur_placement: int
    all_points: int
    all_placement: int
    # completions: list

    def to_dict(self) -> dict:
        return {
            "lccs": self.lcc_count,
            "points_cur": self.cur_points,
            "placement_cur": self.cur_placement,
            "points_all": self.all_points,
            "placement_all": self.all_placement,
        }


@dataclass
class User(PartialUser):
    maplist_profile: MaplistProfile
    created_maps: list[PartialMap]

    def to_dict(self) -> dict:
        return {
            **super().to_dict(),
            "maplist": self.maplist_profile.to_dict(),
            "created_maps": [m.to_dict() for m in self.created_maps],
        }
