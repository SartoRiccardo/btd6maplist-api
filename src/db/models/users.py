from dataclasses import dataclass
from .challenges import ListCompletion


@dataclass
class PartialUser:
    """
    type: object
    properties:
      id:
        type: string
        description: The user's Discord ID.
      name:
        type: string
        description: The user's name.
      is_banned:
        type: boolean
        description: Whether the user's banned.
    ---
    Profile:
      allOf:
      - $ref: "#/components/schemas/PartialUser"
      - type: object
        properties:
          oak:
            type: string
            nullable: true
            description: The user's NinjaKiwi OpenData Access Key
          has_seen_popup:
            type: boolean
            description: |
              Whether the user has already been notified there are rules
              to submissions.
    ---
    ProfilePayload:
      type: object
      properties:
        name:
          type: string
          description: The user's name.
        oak:
          type: string
          nullable: true
          description: The user's NinjaKiwi OpenData Access Key
    """
    id: int
    name: str
    oak: str | None
    has_seen_popup: bool
    is_banned: bool

    def __eq__(self, other):
        if isinstance(other, PartialUser):
            return self.id == other.id and self.name == other.name
        return NotImplemented

    def __hash__(self):
        return hash(f"{self.id}//{self.name}")

    def to_dict(self, profile: bool = False) -> dict:
        extra_fields = {}
        if profile:
            extra_fields = {
                "oak": self.oak,
                "has_seen_popup": self.has_seen_popup,
            }
        return {
            "id": str(self.id),
            "name": self.name,
            "is_banned": self.is_banned,
            **extra_fields,
        }


@dataclass
class MaplistProfile:
    """
    type: object
    properties:
      points:
        type: integer
        description: Points on the leaderboard.
      pts_placement:
        type: integer
        nullable: true
        description: Placement on the points leaderboard.
      lccs:
        type: integer
        description: Number of current LCCs.
      lccs_placement:
        type: integer
        nullable: true
        description: Placement on the LCC leaderboard.
      no_geraldo:
        type: integer
        description: Number of No Optimal Hero completions.
      no_geraldo_placement:
        type: integer
        nullable: true
        description: Placement on the No Optimal Hero leaderboard.
      black_border:
        type: integer
        description: Number of Black Border runs.
      black_border_placement:
        type: integer
        nullable: true
        description: Placement on the Black Border leaderboard.
    """
    points: int
    pts_placement: int | None
    lccs: int
    lccs_placement: int | None
    no_geraldo: int
    no_geraldo_placement: int | None
    black_border: int
    black_border_placement: int | None

    def to_dict(self) -> dict:
        return {
            "points": self.points,
            "pts_placement": self.pts_placement,
            "lccs": self.lccs,
            "lccs_placement": self.lccs_placement,
            "no_geraldo": self.no_geraldo,
            "no_geraldo_placement": self.no_geraldo_placement,
            "black_border": self.black_border,
            "black_border_placement": self.black_border_placement,
        }


@dataclass
class MaplistMedals:
    """
    type: object
    properties:
      wins:
        type: integer
        description: Number of completions.
      black_border:
        type: integer
        description: Number of black border completions.
      no_geraldo:
        type: integer
        description: Number of No Optimal Hero completions.
      lccs:
        type: integer
        description: Number of LCCs.
    """
    wins: int
    black_border: int
    no_geraldo: int
    lccs: int

    def to_dict(self) -> dict:
        return {
            "wins": self.wins,
            "black_border": self.black_border,
            "no_geraldo": self.no_geraldo,
            "lccs": self.lccs,
        }


@dataclass
class MinimalUser(PartialUser):
    """
    allOf:
    - $ref: "#/components/schemas/PartialUser"
    - type: object
      properties:
        permissions:
          type: array
          description: A key-value pair of a format ID and a user's permissions on it.
          items:
            type: object
            properties:
              format:
                type: integer
                nullable: true
                description: The format these perms apply in. `null` if they apply to all formats.
              permissions:
                type: array
                items:
                  type: string
    """
    permissions: "src.db.models.Permissions"
    roles: list["src.db.models.Role"]
    completions: list[ListCompletion]

    def to_dict(
            self,
            profile: bool = False,
            with_completions: bool = False,
    ) -> dict:
        data = {
            **super().to_dict(profile=profile),
            "permissions": self.permissions.to_dict(),
            "roles": [r.to_dict() for r in self.roles],
            "completions": [c.to_profile_dict() for c in self.completions],
        }
        return data


@dataclass
class User(PartialUser):
    """
    allOf:
    - $ref: "#/components/schemas/PartialUser"
    - type: object
      properties:
        list_stats:
          type: array
          description: The user's stats in some lists
          items:
            type: object
            properties:
              format_id:
                $ref: "#/components/schemas/MaplistFormat"
              stats:
                $ref: "#/components/schemas/MaplistProfile"
        created_maps:
          type: array
          items:
            $ref: "#/components/schemas/PartialMap"
        medals:
          $ref: "#/components/schemas/MaplistMedals"
        roles:
          type: array
          items:
            $ref: "#/components/schemas/PartialRole"
        achievement_roles:
          type: array
          items:
            $ref: "#/components/schemas/AchievementRole"
    ---
    FullProfile:
      allOf:
      - $ref: "#/components/schemas/Profile"
      - $ref: "#/components/schemas/User"
    """
    list_stats: dict[int, MaplistProfile]
    created_maps: list["src.db.models.maps.PartialMap"]
    completions: list[ListCompletion]
    medals: MaplistMedals
    roles: list["src.db.models.Role.Role"]
    achievement_roles: list["src.db.models.AchievementRole.AchievementRole"]

    def to_dict(
            self,
            profile: bool = False,
            with_completions: bool = False
    ) -> dict:
        data = {
            **super().to_dict(profile=profile),
            "list_stats": [
                {"format_id": format_id, "stats": self.list_stats[format_id].to_dict()}
                for format_id in self.list_stats
            ],
            "created_maps": [m.to_dict() for m in self.created_maps],
            "medals": self.medals.to_dict(),
            "roles": [r.to_dict() for r in self.roles],
            "achievement_roles": [r.to_dict() for r in self.achievement_roles],
        }
        if with_completions:
            data["completions"] = [c.to_profile_dict() for c in self.completions]
        return data
