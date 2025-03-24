

class Permissions:
    def __init__(self, perms: dict):
        self._perms = perms

    def has(self, perm: str, format: int | list[int] | None) -> bool:
        if perm in self._perms.get(None, []):
            return True

        if isinstance(format, int):
            format = [format]
        elif format is None:
            format = []
        return any(perm in self._perms.get(fmt, []) for fmt in format)

    def has_in_any(self, perm: str) -> bool:
        return any(perm in self._perms[fmt] for fmt in self._perms)

    def has_any_perms(self) -> bool:
        valid_perms = [
            "create:map",
            "edit:map",
            "delete:map",
            "edit:config",
            "create:completion",
            "edit:completion",
            "delete:completion",
            "delete:map_submission",
            "edit:achievement_roles",
            "create:user",
        ]
        return any(
            any(
                valid in self._perms[fmt]
                for valid in valid_perms
            )
            for fmt in self._perms
        )

    def formats_where(self, perm: str) -> list[int | None]:
        return [
            fmt for fmt in self._perms
            if perm in self._perms[fmt]
        ]

    def to_dict(self) -> list[dict]:
        return [
            {"format": k, "permissions": self._perms[k]}
            for k in self._perms
        ]
