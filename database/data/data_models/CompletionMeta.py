from dataclasses import dataclass
from ..data_utils import dateify, SEPARATOR, stringify
from .LCC import LCC


@dataclass
class CompletionMeta:
    comp_id: int
    comp_meta_id: int
    black_border: bool
    no_geraldo: bool
    created_on: int
    deleted_on: int | None
    new_version: int | None
    accepted_by: int | None
    format: int
    lcc: LCC | None
    players: list[int]

    def dump_completion_meta(self) -> str:
        return SEPARATOR.join(stringify(
            self.comp_meta_id,
            self.comp_id,
            self.black_border,
            self.no_geraldo,
            self.lcc.id if self.lcc else None,
            dateify(self.created_on),
            dateify(self.deleted_on),
            self.new_version,
            self.accepted_by,
            self.format,
            None,  # Copied from ID
        ))

    def dump_players(self) -> str:
        return "\n".join(
            SEPARATOR.join(stringify(user_id, self.comp_meta_id))
            for user_id in self.players
        )

