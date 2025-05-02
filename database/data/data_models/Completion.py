from dataclasses import dataclass
from ..data_utils import SEPARATOR, stringify, dateify
from .Map import Map
from .MapKey import MapKey
from .LCC import LCC


@dataclass
class Completion:
    id: int
    map: Map | MapKey
    black_border: bool
    no_geraldo: bool
    created_on: int
    deleted_on: int | None
    new_version: int | None
    accepted_by: int | None
    format: int
    subm_notes: str | None
    subm_wh_payload: str | None
    # One-to-one
    lcc: LCC | None
    # Many-to-one
    players: list[int]
    subm_proof_img: list[str]
    subm_proof_vid: list[str]

    @property
    def comp_meta_id(self):
        return self.id + (-1 if self.id % 2 == 0 else 1)

    def dump_completion(self) -> str:
        return SEPARATOR.join(stringify(
            self.id,
            self.map.code,
            dateify(self.created_on),
            self.subm_notes,
            self.subm_wh_payload,
            None,  # Copied from ID
        ))

    def dump_completion_meta(self) -> str:
        return SEPARATOR.join(stringify(
            self.comp_meta_id,
            self.id,
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

    def dump_proofs(self) -> str:
        return "\n".join([
            *[
                SEPARATOR.join(stringify(self.id, url, 0))
                for url in self.subm_proof_img
            ],
            *[
                SEPARATOR.join(stringify(self.id, url, 1))
                for url in self.subm_proof_vid
            ],
        ])

