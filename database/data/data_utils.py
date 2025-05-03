from typing import Any
from datetime import datetime

NULLSTR = "\\N"
SEPARATOR = "\t"
BR = "\n"


def nullify(data: Any | None) -> str:
    if data is None:
        return NULLSTR
    return str(data)


def num_to_letters(num: int):
    letters = ""
    while num > 0:
        letters = chr(num % 10 + ord('A')) + letters
        num = num // 10
    letters = "A"*max(2-len(letters), 0) + letters
    letters = "X"*max(3-len(letters), 0) + letters
    return letters


def dateify(timestamp: int | None) -> str:
    if timestamp is None:
        return NULLSTR
    date = datetime.fromtimestamp(timestamp)
    return date.strftime("%Y-%m-%d %H:%M:%S.000000")


def stringify(*args: Any) -> list[str]:
    return [nullify(x) for x in args]


def rm_nulls(l: list[Any | None]) -> list:
    return [x for x in l if x is not None]


def difficultify(diff: int) -> str:
    return nullify(None if diff == -1 else diff)