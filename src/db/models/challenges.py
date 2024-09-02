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
    leftover: int
    proof: str

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
    """
    id: int
    map: str | PartialMap
    user_ids: list[int]
    black_border: bool
    no_geraldo: bool
    current_lcc: bool
    format: int
    lcc: LCC | None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "map": self.map.to_dict() if hasattr(self.map, "to_dict") else self.map,
            "user_ids": [str(usr) for usr in self.user_ids],
            "black_border": self.black_border,
            "no_geraldo": self.no_geraldo,
            "current_lcc": self.current_lcc,
            "lcc": self.lcc.to_dict() if self.lcc else None,
            "format": self.format,
        }
