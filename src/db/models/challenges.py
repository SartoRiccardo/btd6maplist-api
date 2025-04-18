import datetime
from dataclasses import dataclass
from .maps import PartialMap


@dataclass
class LCC:
    """
    type: object
    properties:
      leftover:
        type: integer
        description: >
          The amount of cash saved at the end. Since Least Cash rules can't be
          applied to custom maps, saveup is tracked instead of cash spent.
    """
    id: int
    leftover: int

    def to_dict(self) -> dict:
        return {
            "leftover": self.leftover,
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
      users:
        type: array
        description: The players who completed this run.
        items:
          $ref: "#/components/schemas/PartialUser"
      black_border:
        type: boolean
        description: "`true` if the run was black bordered."
      no_geraldo:
        type: boolean
        description: "`true` if the run did not use Geraldo."
      current_lcc:
        type: boolean
        description: "`true` if the run is the current LCC for the map."
      lcc:
        $ref: "#/components/schemas/LCC"
        nullable: true
      format:
        $ref: "#/components/schemas/MaplistFormat"
      subm_proof_img:
        type: array
        items:
          type: string
        description: URL to the proof images used when submitting.
      subm_proof_vid:
        type: array
        items:
          type: string
        description: URL to the proof videos used when submitting.
    ---
    ListCompletionWithMap:
      allOf:
      - $ref: "#/components/schemas/ListCompletion"
      - type: object
        properties:
          map:
            $ref: "#/components/schemas/PartialMap"
    ---
    ListCompletionPayload:
      type: object
      properties:
        black_border:
          type: boolean
          description: Whether the completion is a black border run
        no_geraldo:
          type: boolean
          description: Whether the completion used an optimal hero or not
        format:
          $ref: "#/components/schemas/MaplistFormat"
        user_ids:
          type: array
          items:
            $ref: "#/components/schemas/RequestUserID"
        lcc:
          nullable: true
          description: LCC data for the completion
          type: object
          properties:
            leftover:
              type: integer
              description: How much money was left over at the very end of the run
    """
    id: int
    map: str | PartialMap
    user_ids: list[int] | list["src.db.models.ParialUser"]
    black_border: bool
    no_geraldo: bool
    current_lcc: bool
    format: int
    lcc: LCC | None
    subm_proof_img: list[str]
    subm_proof_vid: list[str]
    subm_notes: str | None

    def to_dict(self) -> dict:
        user_list = [u for u in self.user_ids if u is not None]
        if len(user_list):
            if isinstance(user_list[0], int):
                user_list = sorted(str(usr) for usr in user_list)
            else:
                user_list = [usr.to_dict() for usr in sorted(user_list, key=lambda x: x.id, reverse=True)]

        return {
            "id": self.id,
            "map": self.map.to_dict() if hasattr(self.map, "to_dict") else self.map,
            "users": user_list,
            "black_border": self.black_border,
            "no_geraldo": self.no_geraldo,
            "current_lcc": self.current_lcc,
            "lcc": self.lcc.to_dict() if self.lcc else None,
            "format": self.format,
            "subm_proof_img": self.subm_proof_img if self.subm_proof_img else [],
            "subm_proof_vid": self.subm_proof_vid if self.subm_proof_vid else [],
        }

    def to_profile_dict(self) -> dict:
        return {
            "map": self.map.code if isinstance(self.map, PartialMap) else self.map,
            "black_border": self.black_border,
            "no_geraldo": self.no_geraldo,
            "current_lcc": self.current_lcc,
            "format": self.format,
        }


@dataclass
class ListCompletionWithMeta(ListCompletion):
    """
    allOf:
    - $ref: "#/components/schemas/ListCompletion"
    - type: object
      properties:
        accepted_by:
          $ref: "#/components/schemas/DiscordID"
        created_on:
          type: integer
          nullable: true
          description: |
            Timestamp of the completion's creation date.
            If `accepted_by`, it's when it was accepted. Otherwise, it's when it was submitted.
        deleted_on:
          type: integer
          nullable: true
          description: |
            Timestamp of the completion's deletion. Always `null` if not `accepted_by`.
        subm_notes:
          type: string
          nullable: true
          description: Notes the user put when submitting.
    """
    accepted_by: int | None
    created_on: datetime.datetime | None
    deleted_on: datetime.datetime | None
    subm_wh_payload: str | None  # Message Id;Embed content. Internal use only.

    def to_dict(self) -> dict:
        return {
            **super().to_dict(),
            "subm_notes": self.subm_notes,
            "accepted_by": str(self.accepted_by) if self.accepted_by else None,
            "deleted_on": int(self.deleted_on.timestamp()) if self.deleted_on else None,
            "created_on": int(self.created_on.timestamp()) if self.created_on else None,
        }
