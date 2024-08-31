import asyncio
from typing import Type, Any
import re
import src.utils.routedecos
import src.http
from src.db.queries.maps import map_exists, alias_exists
from src.db.queries.users import get_user_min


MAX_TEXT_LEN = 100
MAX_ADD_CODES = 5


async def validate_map_code(code: str) -> str | None:
    if not isinstance(code, str) or not re.match("^[A-Z]{7}$", code):
        return "Must be a 7 uppercase letter code"
    else:
        nk_response = await src.http.http.get(f"https://data.ninjakiwi.com/btd6/maps/map/{code}")
        if not nk_response.ok or not (await nk_response.json())["success"]:
            return f"There is no map with code {code}"


def get_repeated_indexes(l: list) -> list[int]:
    l_sorted = sorted(enumerate(l), key=lambda x: x[1])
    repeated = []
    for i in range(1, len(l_sorted)):
        if l_sorted[i][1] == l_sorted[i-1][1]:
            repeated.append(l_sorted[i][0])
    return repeated


def check_fields(body: dict | list | Any, schema: dict | list | Type, path: str = "") -> dict:
    if isinstance(body, dict):
        for key in schema:
            if key not in body:
                return {f"{path}.{key}"[1:]: "Missing"}
            if error := check_fields(body[key], schema[key], path=f"{path}.{key}"):
                return error
    elif isinstance(body, list):
        if not isinstance(schema, list):
            return {path[1:]: f"Wrong typing (must be `{schema}`)"}
        for i, item in enumerate(body):
            if error := check_fields(item, schema[0], path=f"{path}[{i}]"):
                return error
    elif not isinstance(body, schema):
        return {path[1:]: f"Wrong typing (must be `{schema}`)"}
    return {}


def typecheck_full_map(body: dict):
    check_fields_exists = {
        "code": str,
        "name": str,
        "placement_allver": int,
        "placement_curver": int,
        "difficulty": int,
        "r6_start": str | None,
        "map_data": str | None,
        "additional_codes": [{"code": str, "description": str | None}],
        "creators": [{"id": str, "role": str | None}],
        "verifiers": [{"id": str, "version": int | None}],
        "aliases": [str],
        "version_compatibilities": [{"version": int, "status": int}],
        # "optimal_heros": [str],
    }
    check = check_fields(body, check_fields_exists)
    if len(check):
        return check


async def validate_full_map(body: dict, check_dup_code: bool = True) -> dict:
    errors = {}
    if check_fail := typecheck_full_map(body):
        return check_fail

    if check_dup_code and await map_exists(body["code"]):
        return {"code": "Map already exists"}
    if code_err := await validate_map_code(body["code"]):
        errors["code"] = code_err
    for i, addcode in enumerate(body["additional_codes"][:MAX_ADD_CODES]):
        if code_err := await validate_map_code(addcode["code"]):
            errors[f"additional_codes[{i}].code"] = code_err
        if addcode["description"] is not None and len(addcode["description"]) > MAX_TEXT_LEN:
            errors[f"additional_codes[{i}].description"] = f"Must be under {MAX_TEXT_LEN} characters"

    if len(body["name"]) > MAX_TEXT_LEN:
        errors["name"] = f"Must be under {MAX_TEXT_LEN} characters"

    rep_alias_idx = get_repeated_indexes(body["aliases"])
    if len(rep_alias_idx):
        for idx in rep_alias_idx:
            errors[f"aliases[{idx}].alias"] = "Duplicate alias"
    else:
        dup_aliases = await asyncio.gather(*[
            alias_exists(alias) for i, alias in body["aliases"]
        ])
        for i, isdup in enumerate(dup_aliases):
            if isdup:
                errors[f"aliases[{i}].alias"] = "Already assigned to another map"

    if len(body["creators"]) == 0:
        errors["creators"] = "Must have at least one creator"
    elif rep_idx := get_repeated_indexes([el["id"] for el in body["creators"]]):
        for idx in rep_idx:
            errors[f"creators[{idx}].id"] = "Duplicate creator"
    else:
        users = await asyncio.gather(*[
            get_user_min(creat["id"]) for creat in body["creators"]
        ])
        for i, usr in enumerate(users):
            if usr is None:
                errors[f"creators[{i}].id"] = "This user doesn't exist"
            else:
                body["creators"][i]["id"] = str(usr.id)
        for i, crt in enumerate(body["creators"]):
            if crt["role"] is not None and len(crt["role"]) > MAX_TEXT_LEN:
                errors[f"creators[{i}].description"] = f"Must be under {MAX_TEXT_LEN} characters"

    users = await asyncio.gather(*[
        get_user_min(verif["id"]) for verif in body["verifiers"]
    ])
    for i, usr in enumerate(users):
        if usr is None:
            errors[f"verifiers[{i}].id"] = "This user doesn't exist"
        else:
            body["verifiers"][i]["id"] = str(usr.id)

    if not (-1 <= body["difficulty"] <= 3):
        errors["difficulty"] = "Must be between -1 and 3, included"
    elif body["difficulty"] <= body["placement_curver"] <= body["placement_allver"] < 0:
        errors["placement_allver"] = "At least one of these should be set"
        errors["placement_curver"] = "At least one of these should be set"
        errors["difficulty"] = "At least one of these should be set"

    for i, vcompat in enumerate(body["version_compatibilities"]):
        if not (0 <= vcompat["status"] <= 3):
            errors[f"version_compatibilities[{i}].status"] = "Must be between 0 and 3, included"

    return errors