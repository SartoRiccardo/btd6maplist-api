from dataclasses import dataclass


@dataclass
class PartialExpertMap:
    """
    type: object
    properties:
      name:
        type: string
        description: The name of the map.
      code:
        type: string
        description: The code of the map.
      difficulty:
        $ref: "#/components/schemas/ExpertDifficulty"
    """
    name: str
    code: str
    difficulty: int

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "code": self.code,
            "difficulty": self.difficulty,
        }


@dataclass
class PartialListMap:
    """
    type: object
    properties:
      name:
        type: string
        description: The map's name.
      code:
        type: string
        description: The map's code.
      placement:
        type: integer
        description: The map's placement in the list (starts from 1).
      verified:
        type: boolean
        description: "`true` if the map was verified in the current update."
    """
    name: str
    code: str
    placement: int
    verified: bool

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "code": self.code,
            "placement": self.placement,
            "verified": self.verified,
        }


@dataclass
class PartialMap:
    """
    type: object
    properties:
      name:
        type: string
        description: The map's name.
      code:
        type: string
        description: The map's code.
      placement_cur:
        type: integer
        description: The map's placement in the list ~ current version (starts from 1). If none, it's set to `-1`.
      placement_all:
        type: integer
        description: The map's placement in the list ~ all versions (starts from 1). If none, it's set to `-1`.
      difficulty:
        $ref: "#/components/schemas/ExpertDifficulty"
      r6_start:
        type: string
        nullable: true
        description: URL to how to start Round 6.
      map_data:
        type: string
        nullable: true
        description: URL to the map data.
    """
    code: str
    name: str
    placement_cur: int | None
    placement_all: int | None
    difficulty: int | None
    r6_start: str | None
    map_data: str

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "name": self.name,
            "placement_all": self.placement_all,
            "placement_cur": self.placement_cur,
            "difficulty": self.difficulty,
            "r6_start": self.r6_start,
            "map_data": self.map_data,
        }


@dataclass
class Map(PartialMap):
    """
    allOf:
    - $ref: "#/components/schemas/PartialMap"
    - type: object
      properties:
        creators:
          type: array
          items:
            type: object
            properties:
              id:
                $ref: "#/components/schemas/DiscordID"
              role:
                type: string
                nullable: true
                description: The contributions the user had in the map's creation
          description: The map's creators
        additional_codes:
          type: array
          items:
            type: object
            properties:
              code:
                type: string
                description: The map's code.
              description:
                type: string
                nullable: true
                description: What this map has different from the original
          description: Additional codes for the map, if any.
        verifications:
          type: array
          items:
            type: object
            properties:
              verifier:
                $ref: "#/components/schemas/DiscordID"
              version:
                type: number
                nullable: true
                description: >
                  The version the map was verified in.
                  If it's the first verification, it's set to `null`.
          description: The users who verified the map
        verified:
          type: boolean
          description: "`true` if the map was verified in the current update."
        lccs:
          $ref: "#/components/schemas/LCC"
        map_data_compatibility:
          type: array
          items:
            type: object
            properties:
              status:
                $ref: "#/components/schemas/MapVersionCompatibility"
              version:
                type: number
                description: The version since this compatibility status came into effect.
          description: >
            Changelog of compatibilities with previous versions.
            It always implicitely starts at v39.0 with it being unavailable.
        aliases:
          type: array
          items:
            type: string
          description: A list of aliases for the map
    """
    creators: list[tuple[int, str | None]]
    additional_codes: list[tuple[str, str | None]]
    verifications: list[tuple[str, float | None]]
    verified: bool
    lccs: list["src.db.models.challenges.LCC"]
    map_data_compatibility: list[tuple[int, int]]
    aliases: list[str]

    def to_dict(self) -> dict:
        compatibility = [*self.map_data_compatibility]
        if len(compatibility) and compatibility[0][1] > 39:
            compatibility.insert(0, (3, 39))

        return {
            **super().to_dict(),
            "lccs": [lcc.to_dict() for lcc in self.lccs],
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
            "aliases": self.aliases,
        }
