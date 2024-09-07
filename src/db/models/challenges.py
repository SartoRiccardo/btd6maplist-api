import datetime
from dataclasses import dataclass
from .maps import PartialMap


@dataclass
class LCC:
    """
    type: object
    properties:
      id:
        type: integer
        description: The unique ID of the LCC.
      leftover:
        type: integer
        description: >
          The amount of cash saved at the end. Since Least Cash rules can't be
          applied to custom maps, saveup is tracked instead of cash spent.
      proof:
        type: string
        description: >
          An URL which links to an image or a video proof of the run being beaten with
          the correct saveup.
    """
    id: int
    proof: str
    leftover: int

    def to_dict(self) -> dict:
        return {
            # "id": self.id,
            "leftover": self.leftover,
            "proof": self.proof,
        }


@dataclass
class ListCompletion:
    """
    type: object
    properties:
      id:
        type: integer
        description: The completion's unique ID
      map:
        type: string
        description: The code of the map that was completed
      user_ids:
        type: array
        description: The players who completed this run. It's an array because some runs can be collabs.
        items:
          type: string
          description: The user's Discord ID.
      black_border:
        type: boolean
        description: "`true` if the run was black bordered."
      no_geraldo:
        type: boolean
        description: "`true` if the run did not use Geraldo."
      current_lcc:
        type: boolean
        description: "`true` if the run is the current LCC for the map."
      format:
        $ref: "#/components/schemas/MaplistFormat"
    ---
    ListCompletionWithMap:
      allOf:
      - $ref: "#/components/schemas/ListCompletion"
      - type: object
        properties:
          map:
            $ref: "#/components/schemas/PartialMap"
    ---
    ListCompletionWithMeta:
      allOf:
      - $ref: "#/components/schemas/ListCompletion"
      - type: object
        properties:
          accepted:
            type: boolean
            description: Whether or not the run was accepted by moderators.
          created_on:
            type: integer
            nullable: true
            description: |
              Timestamp of the completion's creation date.
              If `accepted`, it's when it was accepted. Otherwise, it's when it was submitted.
          deleted_on:
            type: integer
            nullable: true
            description: |
              Timestamp of the completion's deletion. Always `null` if not `accepted`.
    """
    id: int
    map: str | PartialMap
    user_ids: list[int] | list["src.db.models.ParialUser"]
    black_border: bool
    no_geraldo: bool
    current_lcc: bool
    format: int
    lcc: LCC | None
    accepted: bool = True
    deleted_on: datetime.datetime | None = None
    created_on: datetime.datetime | None = None

    def to_dict(self, full: bool = False) -> dict:
        full_args = {}
        if full:
            full_args = {
                "accepted": self.accepted,
                "deleted_on": int(self.deleted_on.timestamp()) if self.deleted_on else None,
                "created_on": int(self.created_on.timestamp()) if self.created_on else None,
            }

        return {
            "id": self.id,
            "map": self.map.to_dict() if hasattr(self.map, "to_dict") else self.map,
            "user_ids": [
                str(usr) if isinstance(usr, int) else usr.to_dict()
                for usr in self.user_ids
            ],
            "black_border": self.black_border,
            "no_geraldo": self.no_geraldo,
            "current_lcc": self.current_lcc,
            "lcc": self.lcc.to_dict() if self.lcc else None,
            "format": self.format,
            **full_args,
        }
