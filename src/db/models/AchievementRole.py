from dataclasses import dataclass


@dataclass
class DiscordRole:
    """
    type: object
    properties:
      guild_id:
        type: integer
        description: The ID of the guild the role is in.
      role_id:
        type: integer
        description: The ID of the role.
    """
    guild_id: int
    role_id: int


@dataclass
class AchievementRole:
    """
    type: object
    properties:
      lb_format:
        $ref: "#/components/schemas/MaplistFormat"
      lb_type:
        type: string
        description: The subtype of the leaderboard.
      threshold:
        type: integer
        description: Point threshold after which the role is granted. Ignored if `for_first` is `true`.
      for_first:
        type: integer
        description: If `true`, this role is awarded for being first place in its leaderboard.
      tooltip_description:
        type: string
        description: Short description of the role.
        nullable: true
      name:
        type: string
        description: The name of the role.
      clr_border:
        type: integer
        description: The color of the inside of the role.
      clr_inner:
        type: integer
        description: The name of the border of the role.
      linked_roles:
        type: array
        items:
          $ref: "#/components/schemas/DiscordRole"
        description: The Discord roles linked to this role, if any
    """
    id: int
    lb_format: int
    lb_type: str
    threshold: int
    for_first: bool
    tooltip_description: str | None
    name: str
    clr_border: int
    clr_inner: int
    linked_roles: list[DiscordRole]
