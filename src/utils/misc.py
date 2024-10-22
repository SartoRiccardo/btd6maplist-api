from functools import lru_cache

list_to_int = ["list", "experts"]
MAPLIST_FORMATS = [1, 2, 51]


@lru_cache()
def point_formula(idx, points_btm, points_top, map_count, slope) -> float:
    return points_btm * (points_top / points_btm) ** ((1 + (1 - idx) / (map_count - 1)) ** slope)


def list_eq(l1, l2) -> bool:
    if len(l1) != len(l2):
        return False
    for i in range(len(l1)):
        if l1[i] != l2[i]:
            return False
    return True


def list_rm_dupe(lst: list | None, preserve_order: bool = True) -> list:
    if lst is None:
        return []

    if not preserve_order:
        return list(set(lst))

    unique = []
    for item in lst:
        if item not in unique:
            unique.append(item)
    return unique


def index_where(l: list, cond) -> int:
    for i in range(len(l)):
        if cond(l[i]):
            return i
    return -1


def aggregate_payload(
        payload: list,
        distinct_range: range = None,
        to_group_range: range = None,
):
    di_s = distinct_range.start
    di_e = distinct_range.stop
    tgi_s = to_group_range.start

    new_pl = []
    current = None
    unchanged = None
    grouped = None
    for row in payload:
        if current is None or not list_eq(current, row[di_s:di_e]):
            if current is not None:
                new_pl.append([*current, *unchanged, *[list(set(f)) for f in grouped]])
            current = row[di_s:di_e]
            unchanged = row[di_e:tgi_s]
            grouped = [[] for _ in to_group_range]
        for i in to_group_range:
            grouped[i-tgi_s].append(row[i])
    new_pl.append([*current, *unchanged, *[list(set(f)) for f in grouped]])
    return new_pl
