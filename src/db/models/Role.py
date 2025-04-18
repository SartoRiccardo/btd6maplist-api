from dataclasses import dataclass, field


@dataclass
class Role:
    """
    allOf:
    - $ref: "#/components/schemas/PartialRole"
    - type: object
      properties:
        can_grant:
          description: The IDs of the roles it can grant.
          type: array
          items:
            type: integer
    ---
    PartialRole:
      type: object
      properties:
        id:
          type: integer
          description: The ID of the role.
        name:
          type: string
          description: The name of the role.
    """
    id: int
    name: str
    can_grant: list[int] = field(default_factory=list)

    def to_dict(self, full: bool = False):
        full_fields = {}
        if full:
            full_fields = {
                "can_grant": self.can_grant,
            }

        return {
            "id": self.id,
            "name": self.name,
            **full_fields,
        }
