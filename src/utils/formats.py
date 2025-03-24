from .misc import MAPLIST_FORMATS
from dataclasses import dataclass
from src.db.queries.misc import get_config
from src.db.queries.format import get_format
from collections.abc import Awaitable, Callable
from src.utils.cache import cache_for

ReqRecArgs = ["src.db.models.PartialMap", bool, bool, bool]
ValidatorReturns = tuple[bool, str | None, bool]


class FormatStatus:
    CLOSED = 0
    OPEN = 1
    LCC_ONLY = 2


@dataclass
class FormatInfo:
    key: str
    validate: Callable[[int], Awaitable[ValidatorReturns]]
    run_requires_recording: Callable[ReqRecArgs, bool]


class FormatValueValidators:
    @staticmethod
    async def placement_curver(val: int) -> ValidatorReturns:
        config = await get_config()
        map_count = config["map_count"]
        error_msg = None
        if 0 <= val:
            error_msg = f"Must be between 1 and {map_count}, or be left unchanged if already over {map_count}"
        return 0 <= val, error_msg, val > map_count

    @staticmethod
    async def difficulty(val: int) -> ValidatorReturns:
        valid = 0 <= val <= 4
        error_msg = None if valid else "Must be between 0 and 4, included"
        return valid, error_msg, False

    @staticmethod
    async def np_map(val: int) -> ValidatorReturns:
        return True, None, False


format_idxs = {
    1: FormatInfo(
        "placement_curver",
        FormatValueValidators.placement_curver,
        lambda on_map, bb, noh, lcc: bb or lcc or noh,
    ),
    2: FormatInfo(
        "placement_allver",
        FormatValueValidators.placement_curver,
        lambda on_map, bb, noh, lcc: bb or lcc or noh,
    ),
    11: FormatInfo(
        "remake_of",
        FormatValueValidators.np_map,
        lambda on_map, bb, noh, lcc: False,
    ),
    51: FormatInfo(
        "difficulty",
        FormatValueValidators.difficulty,
        lambda on_map, bb, noh, lcc: bb or lcc or noh and not (0 <= on_map.difficulty <= 2),
    ),
    52: FormatInfo(
        "botb_difficulty",
        FormatValueValidators.difficulty,
        lambda on_map, bb, noh, lcc: False,
    ),
}


@cache_for(60)
async def get_maplist_map_count():
    return (await get_config())["map_count"]
