

def is_format_valid(f: int) -> bool:
    return 0 <= f < 100


def is_format_maplist(f: int) -> bool:
    return 0 <= f < 50


def is_format_expert(f: int) -> bool:
    return 50 <= f < 100


def format_exists(f: int) -> bool:
    return f in [1, 2, 51]
