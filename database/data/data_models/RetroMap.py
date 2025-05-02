from dataclasses import dataclass
from ..data_utils import SEPARATOR, stringify


@dataclass
class RetroMap:
    id: int
    name: str
    sort_order: int
    game: int
    difficulty: int
    subcategory: int

    def dump_retro_map(self) -> str:
        return SEPARATOR.join(stringify(
            self.id,
            self.name,
            self.sort_order,
            '',
            self.game,
            self.difficulty,
            self.subcategory,
        ))
