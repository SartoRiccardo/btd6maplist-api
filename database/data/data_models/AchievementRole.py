from dataclasses import dataclass
from ..data_utils import SEPARATOR, stringify


@dataclass
class AchievementRole:
    lb_format: int
    lb_type: str
    threshold: int
    for_first: bool
    tooltip_description: str | None
    name: str
    clr_border: int
    clr_inner: int
    # Many-to-one
    linked_roles: list[tuple[int, int]]

    def dump_ach_roles(self) -> str:
        return SEPARATOR.join(stringify(
            self.lb_format,
            self.lb_type,
            self.threshold,
            self.for_first,
            self.tooltip_description,
            self.name,
            self.clr_border,
            self.clr_inner,
        ))

    def dump_linked_roles(self) -> str:
        return "\n".join([
            SEPARATOR.join(
                stringify(self.lb_format, self.lb_type, self.threshold, guild, role)
            )
            for guild, role in self.linked_roles
        ])
