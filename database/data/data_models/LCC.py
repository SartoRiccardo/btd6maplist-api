from dataclasses import dataclass
from ..data_utils import SEPARATOR, stringify


@dataclass
class LCC:
    id: int
    leftover: int

    def dump_lcc(self):
        return SEPARATOR.join(stringify(
            self.id,
            self.leftover,
        ))
