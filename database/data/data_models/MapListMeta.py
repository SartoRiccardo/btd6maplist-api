from dataclasses import dataclass
from ..data_utils import SEPARATOR, difficultify, stringify, dateify


@dataclass
class MapListMeta:
    id: int
    code: str
    placement_cur: int
    placement_all: int
    difficulty: int
    deleted_on: int | None
    new_version: int | None
    created_on: int
    optimal_heros: list[str]
    botb_difficulty: int | None = None
    remake_of: int | None = None

    def dump_map_meta(self) -> str:
        return SEPARATOR.join(stringify(
            self.id,
            self.code,
            difficultify(self.placement_cur),
            difficultify(self.placement_all),
            difficultify(self.difficulty),
            ";".join(self.optimal_heros),
            difficultify(self.botb_difficulty),
            difficultify(self.remake_of),
            dateify(self.created_on),
            dateify(self.deleted_on),
        ))