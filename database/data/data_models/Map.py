from dataclasses import dataclass
from ..data_utils import SEPARATOR, nullify, difficultify, stringify, dateify


@dataclass
class Map:
    id: int
    code: str
    name: str
    placement_cur: int
    placement_all: int
    difficulty: int
    r6_start: str | None
    deleted_on: int | None
    map_preview_url: str | None
    new_version: int | None
    created_on: int
    optimal_heros: list[str]
    # Many-To-One
    creators: list[tuple[int, str | None]]
    additional_codes: list[tuple[str, str | None]]
    verifications: list[tuple[str, int]]
    map_data_compatibility: list[tuple[int, int]]
    aliases: list[str]
    # New fields
    botb_difficulty: int | None = None
    remake_of: int | None = None

    def dump_map(self) -> str:
        return SEPARATOR.join(stringify(
            self.code,
            self.name,
            nullify(self.r6_start),
            nullify(None),
            nullify(self.map_preview_url),
        ))

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
            nullify(self.new_version),
        ))

    def dump_aliases(self) -> str:
        return "\n".join(
            SEPARATOR.join(
                stringify(alias, self.code)
            ) for alias in self.aliases
        )

    def dump_add_codes(self) -> str:
        return "\n".join(
            SEPARATOR.join(
                stringify(code, descr, self.code)
            ) for code, descr in self.additional_codes
        )

    def dump_verifications(self) -> str:
        return "\n".join(
            SEPARATOR.join(
                stringify(user_id, nullify(version), self.code)
            ) for user_id, version in self.verifications
        )

    def dump_creators(self) -> str:
        return "\n".join(
            SEPARATOR.join(
                stringify(user_id, nullify(role), self.code)
            ) for user_id, role in self.creators
        )
