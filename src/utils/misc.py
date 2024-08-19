from functools import lru_cache


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


def index_where(l: list, cond) -> int:
    for i in range(len(l)):
        if cond(l[i]):
            return i
    return -1
