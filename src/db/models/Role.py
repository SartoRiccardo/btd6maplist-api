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
        edit_maplist:
          type: boolean
          description: Whether this role can edit the Maplist.
        edit_experts:
          type: boolean
          description: Whether this role can edit the Expert List.
        requires_recording:
          type: boolean
          description: Whether this role requires video proof when submitting.
        cannot_submit:
          type: boolean
          description: Whether this role is banned.
    """
    id: int
    name: str
    edit_maplist: bool
    edit_experts: bool
    requires_recording: bool
    cannot_submit: bool
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
            "edit_maplist": self.edit_maplist,
            "edit_experts": self.edit_experts,
            "requires_recording": self.requires_recording,
            "cannot_submit": self.cannot_submit,
            **full_fields,
        }
