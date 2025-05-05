from typing import Literal

LeaderboardType = Literal["points", "lccs", "no_geraldo", "black_border"]
formats_str = {1: "maplist", 2: "maplist_all", 51: "experts"}
lb_type_to_function = {
    "lccs": "leaderboard_lccs",
    "no_geraldo": "leaderboard_no_geraldo",
    "black_border": "leaderboard_black_border",
}


def get_int_config(varname):
    return f"(SELECT value FROM config WHERE name='{varname}')::int"


def leaderboard_name(format: int, type: LeaderboardType):
    if not isinstance(format, int):
        raise TypeError("format is not int")
    if type == "points":
        return f"leaderboard_{formats_str[format]}_points" if format in formats_str else None
    # No it's not SQL injection I'm very sure this is an integer
    return f"{lb_type_to_function[type]}({format})"
