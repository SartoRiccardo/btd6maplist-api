from functools import lru_cache


@lru_cache()
def point_formula(idx, points_btm, points_top, map_count, slope) -> float:
    return points_btm * (points_top / points_btm) ** ((1 + (1 - idx) / (map_count - 1)) ** slope)
