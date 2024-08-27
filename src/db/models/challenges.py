from dataclasses import dataclass
from .maps import PartialMap


@dataclass
class LCC:
    """
    type: object
    properties:
      id:
        type: integer
        description: The unique ID of the run.
      leftover:
        type: integer
        description: >
          The amount of cash saved at the end. Since Least Cash rules can't be
          applied to custom maps, saveup is tracked instead of cash spent.
      proof:
        type: string
        description: >
          An URL which links to an image or a video proof of the run being beaten with
          the correct saveup
      format:
        $ref: "#/components/schemas/MaplistFormat"
      players:
        type: array
        items:
          $ref: "#/components/schemas/DiscordID"
        description: The players who took part in the run. Oftentimes it's a single item.
    """
    id: int
    leftover: int
    proof: str
    format: int
    players: list[int]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "leftover": self.leftover,
            "proof": self.proof,
            "format": self.format,
            "players": [str(p) for p in self.players],
        }


@dataclass
class ListCompletion:
    """
    type: object
    properties:
      map:
        type: string
        description: The code of the map that was completed
      user_id:
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
      formats:
        type: array
        items:
          $ref: "#/components/schemas/MaplistFormat"
        description: A list of Maplist formats this run was valid in.
    ---
    ListCompletionWithMap:
      allOf:
      - $ref: "#/components/schemas/ListCompletion"
      - type: object
        properties:
          map:
            $ref: "#/components/schemas/PartialMap"
    """
    map: str | PartialMap
    user_id: int
    black_border: bool
    no_geraldo: bool
    current_lcc: bool
    formats: list[int]

    def to_dict(self) -> dict:
        return {
            "map": self.map.to_dict() if hasattr(self.map, "to_dict") else self.map,
            "user_id": str(self.user_id),
            "black_border": self.black_border,
            "no_geraldo": self.no_geraldo,
            "current_lcc": self.current_lcc,
            "formats": self.formats,
        }
