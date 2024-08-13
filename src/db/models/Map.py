from dataclasses import dataclass
from .challenges import LCC


@dataclass
class Map:
    code: str
    name: str
    creators: list[tuple[int, str | None]]
    additional_codes: list[tuple[str, str | None]]
    verifications: list[tuple[str, float | None]]
    verified: bool
    placement_cur: int | None
    placement_all: int | None
    difficulty: int | None
    lcc: LCC
    r6_start: str | None
    map_data: str
    map_data_compatibility: list[tuple[int, int]]

    def to_dict(self) -> dict:
        compatibility = [*self.map_data_compatibility]
        if len(compatibility) and compatibility[0][1] > 39:
            compatibility.insert(0, (3, 39))

        return {
            "code": self.code,
            "name": self.name,
            "placement_all": self.placement_all,
            "placement_cur": self.placement_cur,
            "difficulty": self.difficulty,
            "lcc": self.lcc.to_dict() if self.lcc else None,
            "r6_start": self.r6_start,
            "map_data": self.map_data,
            "creators": [
                {"id": str(creat), "role": role}
                for creat, role in self.creators
            ],
            "additional_codes": [
                {"code": str(code), "description": descr}
                for code, descr in self.additional_codes
            ],
            "verifications": [
                {"verifier": str(verif), "version": version}
                for verif, version in self.verifications
            ],
            "verified": self.verified,
            "map_data_compatibility": [
                {"status": status, "version": version}
                for status, version in compatibility
            ],
        }
