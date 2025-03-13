from .misc import MAPLIST_FORMATS


def is_format_maplist(f: int) -> bool:
    return 0 <= f < 50


def is_format_expert(f: int) -> bool:
    return 50 <= f < 100


def format_exists(f: int) -> bool:
    return f in MAPLIST_FORMATS


is_format_valid = format_exists
