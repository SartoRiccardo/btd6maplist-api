from dataclasses import dataclass, field


@dataclass
class RoleMock:
    id: int
    name: str
    position: int = 0
    managed: bool = False

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "position": self.position,
            "managed": self.managed,
        }


@dataclass
class MemberMock:
    roles: list[RoleMock] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "roles": [str(r.id) for r in self.roles],
        }


@dataclass
class GuildMock:
    id: int
    name: str
    owner: bool = False
    permissions: int = 0
    roles: list[RoleMock] = field(default_factory=list)
    member: MemberMock | None = None

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": str(self.name),
            "permissions": str(self.permissions),
            "owner": self.owner,
            "roles": [r.to_dict() for r in self.roles],
        }
