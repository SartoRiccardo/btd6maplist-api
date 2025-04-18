from .formats import format_keys
from dataclasses import dataclass
import src.db.queries.maps
import src.db.queries.misc
from src.exceptions import ValidationException
from src.db.models import MinimalMap
from collections.abc import Awaitable, Callable
from src.utils.cache import cache_for

ReqRecArgs = ["src.db.models.PartialMap", bool, bool, bool]
ValidatorReturns = tuple[bool, str | None, bool]


class FormatStatus:
    CLOSED = 0
    OPEN = 1
    LCC_ONLY = 2
    OPEN_CHIMPS = 2


@dataclass
class FormatInfo:
    key: str
    validate: Callable[[int], Awaitable[ValidatorReturns]]
    run_requires_recording: Callable[ReqRecArgs, bool]
    can_accept_run: Callable[["src.db.models.PartialMap"], Awaitable[bool]]
    get_maps: Callable[[int | None], Awaitable[list[MinimalMap]]]
    proposed_values: tuple[str, list[str]] | Callable[[int], Awaitable[str, str]]


class FormatValueValidators:
    @staticmethod
    async def placement_curver(val: int) -> ValidatorReturns:
        map_count = await get_maplist_map_count()
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


class KeyChecks:
    @staticmethod
    def key_is_not_null(key: str):
        async def check(on_map: "src.db.models.PartialMap") -> bool:
            return getattr(on_map, key) is not None
        return check

    @staticmethod
    def within_map_count(key: str):
        async def check(on_map: "src.db.models.PartialMap") -> bool:
            placement = getattr(on_map, key)
            return placement is not None and 0 < getattr(on_map, key) <= await get_maplist_map_count()
        return check


class MapGetter:
    @staticmethod
    def maplist(format_id: int = 1):
        async def getter(_: int | None):
            return await src.db.queries.maps.get_list_maps(curver=format_id == 1)
        return getter

    @staticmethod
    def by_key(key: str, requires_filter: bool = False):
        async def getter(filter_val: int | None):
            if filter_val is None and requires_filter:
                raise ValidationException({"filter": "Filter is required for this format"})
            return await src.db.queries.maps.get_maps_by_idx(key, filter_val)
        return getter

    @staticmethod
    def nostalgia_pack():
        async def getter(filter_val: int | None):
            if filter_val is None:
                raise ValidationException({"filter": "Filter is required for this format"})
            return await src.db.queries.maps.get_nostalgia_pack(filter_val)
        return getter


class GetProposed:
    @staticmethod
    async def nostalgia_pack(proposed: int) -> tuple[str, str]:
        remade_map = await src.db.queries.maps.get_retro_map(proposed)
        if remade_map is None:
            raise ValidationException({"proposed": "There is no retro map with that ID"})
        return "Remake", remade_map.name


format_info = {
    1: FormatInfo(
        format_keys[1],
        FormatValueValidators.placement_curver,
        lambda on_map, bb, noh, lcc: bb or lcc or noh,
        KeyChecks.within_map_count("placement_curver"),
        MapGetter.maplist(1),
        ("List Position", ["Top 3", "Top 10", "#11 ~ 20", "#21 ~ 30", "#31 ~ 40", "#41 ~ 50"]),
    ),
    2: FormatInfo(
        format_keys[2],
        FormatValueValidators.placement_curver,
        lambda on_map, bb, noh, lcc: bb or lcc or noh,
        KeyChecks.within_map_count("placement_allver"),
        MapGetter.maplist(2),
        ("List Position", ["Top 3", "Top 10", "#11 ~ 20", "#21 ~ 30", "#31 ~ 40", "#41 ~ 50"]),
    ),
    11: FormatInfo(
        format_keys[11],
        FormatValueValidators.np_map,
        lambda on_map, bb, noh, lcc: False,
        KeyChecks.key_is_not_null("remake_of"),
        MapGetter.nostalgia_pack(),
        GetProposed.nostalgia_pack,
    ),
    51: FormatInfo(
        format_keys[51],
        FormatValueValidators.difficulty,
        lambda on_map, bb, noh, lcc: bb or lcc or noh and not (0 <= on_map.difficulty <= 2),
        KeyChecks.key_is_not_null("difficulty"),
        MapGetter.by_key("difficulty"),
        ("Difficulty", ["Casual Expert", "Casual/Medium Expert", "Medium Expert", "Medium/High Expert", "High Expert",
                        "High/True Expert", "True Expert", "True/Extreme Expert", "Extreme Expert"]),
    ),
    52: FormatInfo(
        format_keys[52],
        FormatValueValidators.difficulty,
        lambda on_map, bb, noh, lcc: False,
        KeyChecks.key_is_not_null("botb_difficulty"),
        MapGetter.by_key("botb_difficulty", requires_filter=True),
        ("Difficulty", ["Beginner", "Intermediate", "Advanced", "Expert/Extreme"])
    ),
}

if len(format_info.keys()) != len(format_keys.keys()):
    raise NotImplementedError()


@cache_for(60)
async def get_maplist_map_count():
    return (await src.db.queries.misc.get_config())["map_count"].value
