from dataclasses import dataclass
from datetime import datetime


@dataclass
class RetroMap:
    """
    type: object
    """
    sort_order: int
    game_id: int
    difficulty_id: int
    subcategory_id: int
    game_name: str
    difficulty_name: str
    subcategory_name: str

    def to_dict(self) -> dict:
        return {
            "sort_order": self.sort_order,
            "game": {"id": self.game_id, "name": self.game_name},
            "difficulty": {"id": self.difficulty_id, "name": self.difficulty_name},
            "subcategory": {"id": self.subcategory_id, "name": self.subcategory_name},
        }


@dataclass
class MinimalMap:
    """
    type: object
    properties:
      name:
        type: string
        description: The map's name.
      code:
        type: string
        description: The map's code.
      format_idx:
        type: integer
        description: The map's placement in the requested format.
      verified:
        type: boolean
        description: "`true` if the map was verified in the current update."
      map_preview_url:
        type: string
        nullable: true
        description: URL to the map preview.
    """
    name: str
    code: str
    format_idx: int | RetroMap
    verified: bool
    map_preview_url: str | None

    def to_dict(self) -> dict:
        format_value = self.format_idx
        if isinstance(self.format_idx, RetroMap):
            format_value = self.format_idx.to_dict()

        return {
            "name": self.name,
            "code": self.code,
            "format_idx": format_value,
            "verified": self.verified,
            "map_preview_url": self.map_preview_url if self.map_preview_url else
                f"https://data.ninjakiwi.com/btd6/maps/map/{self.code}/preview",
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
      placement_curver:
        type: integer
        nullable: true
        description: The map's placement in the list ~ current version (starts from 1). If none, it's set to `-1`.
      placement_allver:
        type: integer
        nullable: true
        description: The map's placement in the list ~ all versions (starts from 1). If none, it's set to `-1`.
      difficulty:
        $ref: "#/components/schemas/ExpertDifficulty"
      remake_of:
        type: integer
        nullable: true
        description: Which map this is a remake of.
      botb_difficulty:
        type: integer
        nullable: true
        description: The map's Best of the Best pack difficulty.
      r6_start:
        type: string
        nullable: true
        description: URL to how to start Round 6.
      map_data:
        type: string
        nullable: true
        description: URL to the map data.
      map_preview_url:
        type: string
        nullable: true
        description: URL to the map preview.
      optimal_heros:
        type: array
        items:
          $ref: "#/components/schemas/Btd6Hero"
      deleted_on:
        type: integer
        nullable: true
        description: Timestamp of the map's deletion (in seconds).
    """
    code: str
    name: str
    placement_curver: int | None
    placement_allver: int | None
    difficulty: int | None
    botb_difficulty: int | None
    remake_of: int | None
    r6_start: str | None
    map_data: str
    deleted_on: datetime | None
    optimal_heros: list[str]
    map_preview_url: str | None

    @property
    def id(self):
        return self.code

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "name": self.name,
            "placement_allver": self.placement_allver,
            "placement_curver": self.placement_curver,
            "difficulty": self.difficulty,
            "botb_difficulty": self.botb_difficulty,
            "remake_of": self.remake_of,
            "r6_start": self.r6_start,
            "map_data": self.map_data,
            "optimal_heros": [oh for oh in self.optimal_heros if len(oh)],
            "deleted_on": int(self.deleted_on.timestamp()) if self.deleted_on else None,
            "map_preview_url": self.map_preview_url if self.map_preview_url else
                f"https://data.ninjakiwi.com/btd6/maps/map/{self.code}/preview",
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
              name:
                type: str
                description: The username of the creator
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
              name:
                type: string
                description: The username of the verifier
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
          type: array
          items:
            $ref: "#/components/schemas/ListCompletion"
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
          description: |
            Changelog of compatibilities with previous versions.
            It always implicitly starts at v39.0 with it being unavailable.
        aliases:
          type: array
          items:
            type: string
          description: A list of aliases for the map
    ---
    MapPayload:
      type: object
      properties:
        name:
          type: string
          description: The map's name.
        code:
          type: string
          description: The map's code.
        placement_curver:
          type: integer
          description: The map's placement in the list ~ current version (starts from 1). If none, set to `-1`.
        placement_allver:
          type: integer
          description: The map's placement in the list ~ all versions (starts from 1). If none, set to `-1`.
        difficulty:
          $ref: "#/components/schemas/ExpertDifficulty"
        r6_start:
          type: string
          nullable: true
          description: |
            URL to how to start Round 6. Can be an image or a YouTube URL. Takes priority
            over the one provided in the form data.
        map_data:
          type: string
          nullable: true
          description: URL to the map data. #DEPRECATED
        creators:
          type: array
          items:
            type: object
            properties:
              id:
                $ref: "#/components/schemas/RequestUserID"
              role:
                type: string
                nullable: true
                description: The contributions the user had in the map's creation
          description: The map's creators
        additional_codes:
          description: Additional codes for the map, if any.
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
                description: What this map has different from the original.
        verifiers:
          description: The users who verified the map
          type: array
          items:
            type: object
            properties:
              id:
                $ref: "#/components/schemas/RequestUserID"
              version:
                type: number
                nullable: true
                description: >
                  The version the map was verified in.
                  If it's the first verification, it's set to `null`.
        aliases:
          description: A list of aliases for the map
          type: array
          items:
            type: string
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
          description: |
            Changelog of compatibilities with previous versions.
            It always implicitly starts at v39.0 with it being unavailable.
        map_preview_url:
          type: string
          nullable: true
          description: URL to the map preview. Takes priority over the one provided in the form data.
        optimal_heros:
          type: array
          items:
            $ref: "#/components/schemas/Btd6Hero"
    """
    creators: list[tuple[int, str | None, str]]  # TODO tuple role, PartialUser
    additional_codes: list[tuple[str, str | None]]
    verifications: list[tuple[str, float | None, str]]   # TODO tuple version, PartialUser
    verified: bool
    lccs: list["src.db.models.challenges.ListCompletion"]
    map_data_compatibility: list[tuple[int, int]]
    aliases: list[str]

    def to_dict(self) -> dict:
        compatibility = [*self.map_data_compatibility]
        if len(compatibility) and compatibility[0][1] > 390:
            compatibility.insert(0, (3, 390))

        return {
            **super().to_dict(),
            "lccs": [lcc.to_dict() for lcc in self.lccs],
            "creators": [
                {"id": str(creat), "role": role, "name": creat_name}
                for creat, role, creat_name in self.creators
            ],
            "additional_codes": [
                {"code": str(code), "description": descr}
                for code, descr in self.additional_codes
            ],
            "verifications": [
                {"verifier": str(verif), "version": version, "name": verif_name}
                for verif, version, verif_name in self.verifications
            ],
            "verified": bool(self.verified),
            "map_data_compatibility": [
                {"status": status, "version": version}
                for status, version in compatibility
            ],
            "aliases": self.aliases,
        }
