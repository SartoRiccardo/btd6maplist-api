from typing import Literal

LeaderboardType = Literal["points", "lccs", "no_geraldo", "black_border"]
formats_str = {1: "maplist", 2: "maplist_all", 51: "experts"}


def get_int_config(varname):
    return f"(SELECT value FROM config WHERE name='{varname}')::int"


def leaderboard_name(format: int, type: LeaderboardType):
    return f"leaderboard_{formats_str[format]}_{type}"
