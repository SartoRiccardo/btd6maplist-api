import asyncio
import validators
from aiohttp import web
import http
from typing import Type, Any
import re
import src.utils.routedecos
import src.http
from src.db.models import MapSubmission
from src.db.queries.maps import map_exists, alias_exists, get_map
from src.db.queries.users import get_user_min
from src.db.queries.mapsubmissions import get_map_submission


MAX_TEXT_LEN = 100
MAX_LONG_TEXT_LEN = 500
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


def typecheck_full_map(body: dict) -> dict:
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
        "optimal_heros": [str],
        "map_preview_url": str | None,
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
        map_res = await get_map(body["code"])

        async def check_alias(a: str):
            return not (map_res is None or a in map_res.aliases) and await alias_exists(a)
        dup_aliases = await asyncio.gather(*[
            check_alias(alias) for alias in body["aliases"]
        ])
        for i, isdup in enumerate(dup_aliases):
            if isdup:
                errors[f"aliases[{i}].alias"] = "Already assigned to another map"

    if body["r6_start"] and not validators.url(body["r6_start"]):
        errors["r6_start"] = "Must be a URL"
    if body["map_preview_url"] and not validators.url(body["map_preview_url"]):
        errors["map_preview_url"] = "Must be a URL"

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

    if not (-1 <= body["difficulty"] <= 4):
        errors["difficulty"] = "Must be between -1 and 4, included"
    elif body["difficulty"] <= body["placement_curver"] <= body["placement_allver"] < 0:
        errors["placement_allver"] = "At least one of these should be set"
        errors["placement_curver"] = "At least one of these should be set"
        errors["difficulty"] = "At least one of these should be set"
    # FIMXE: Should take 50 from config
    if body["placement_curver"] > 50:
        del body["placement_curver"]
    if body["placement_allver"] > 50:
        del body["placement_allver"]

    for i, vcompat in enumerate(body["version_compatibilities"]):
        if not (0 <= vcompat["status"] <= 3):
            errors[f"version_compatibilities[{i}].status"] = "Must be between 0 and 3, included"

    allowed_heros = [
        "quincy", "gwen", "obyn", "striker", "churchill", "ben", "ezili", "pat", "adora", "brickell", "etienne",
        "sauda", "psi", "geraldo", "corvus", "rosalia",
    ]
    for i, hero in enumerate(body["optimal_heros"]):
        if hero not in allowed_heros:
            errors["optimal_heros[i].hero"] = "That hero doesn't exist"

    return errors


def typecheck_submission(body: dict) -> dict:
    check_fields_exists = {
        "code": str,
        "notes": str | None,
        "proposed": int,
        "type": str,
    }
    check = check_fields(body, check_fields_exists)
    if len(check):
        return check


async def validate_submission(body: dict) -> dict:
    if check_fail := typecheck_submission(body):
        return check_fail

    errors = {}
    if await map_exists(body["code"]):
        return {"code": "Map already exists"}
    if body["notes"] and len(body["notes"]) > MAX_LONG_TEXT_LEN:
        errors["notes"] = f"Must be under {MAX_LONG_TEXT_LEN} characters"
    if body["type"] not in ["list", "experts"]:
        errors["type"] = f"Must be either `list` or `experts`"
    return errors


async def validate_completion_submission(body: dict) -> dict:
    check_fields_exists = {
        "format": int,
        "notes": str | None,
        "black_border": bool,
        "no_geraldo": bool,
        "current_lcc": bool,
    }
    check = check_fields(body, check_fields_exists)
    if len(check):
        return check

    errors = {}
    if body.get("video_proof_url", None) and not validators.url(body["video_proof_url"]):
        errors["video_proof_url"] = "Invalid video URL"
    if (body["black_border"] or body["no_geraldo"] or body["current_lcc"]) and \
            "video_proof_url" not in body:
        errors["video_proof_url"] = "Missing or invalid URL"
    if body["current_lcc"]:
        if "leftover" not in body or not isinstance(body["leftover"], int):
            errors["leftover"] = "Missing or non-integer saveup"
        elif 0 > body["leftover"]:
            errors["leftover"] = "Must be greater than 0"
    if body["format"] not in [1, 2, 51]:
        errors["format"] = "Must be a valid format"
    return errors


async def validate_completion(body: dict) -> dict[str, str]:
    check_fields_exists = {
        "black_border": bool,
        "no_geraldo": bool,
        "format": int,
        "user_ids": [str],
    }
    if len(check := check_fields(body, check_fields_exists)):
        return check
    if "lcc" not in body:
        return {"lcc": "Missing"}

    errors = {}

    if body["lcc"] is not None:
        check_lcc_exists = {
            "leftover": int,
        }
        if len(check := check_fields(body["lcc"], check_lcc_exists)):
            return check

        if "proof_completion" in body["lcc"] and not validators.url(body["lcc"]["proof_completion"]):
            errors["lcc.proof_url"] = "Must be a valid URL"
        elif 0 > body["lcc"]["leftover"]:
            errors["lcc.leftover"] = "Must be greater than 0"

    if body["format"] not in [1, 2, 51]:
        errors["format"] = "Must be a valid format"

    if len(body["user_ids"]) == 0:
        errors["user_ids"] = "Must be beaten by someone"
    elif rep_idx := get_repeated_indexes(body["user_ids"]):
        for idx in rep_idx:
            errors[f"user_ids[{idx}]"] = "Duplicate user ID"
    else:
        users = await asyncio.gather(*[
            get_user_min(uid) for uid in body["user_ids"]
        ])
        for i, usr in enumerate(users):
            if usr is None:
                errors[f"user_ids[{i}]"] = "This user doesn't exist"
            else:
                body["user_ids"][i] = str(usr.id)

    return errors


async def validate_discord_user(body: dict) -> dict[str, str]:
    check_fields_exists = {
        "discord_id": str,
        "name": str,
    }
    if len(check := check_fields(body, check_fields_exists)):
        return check

    errors = {}

    if not body["discord_id"].isnumeric():
        errors["discord_id"] = "Must be numeric"
    else:
        body["discord_id"] = int(body["discord_id"])
    body["name"] = body["name"].lower()

    return errors


async def check_prev_map_submission(
        code: str,
        submitter: str
) -> MapSubmission | web.Response | None:
    prev_submission = await get_map_submission(code)
    if prev_submission is not None:
        if prev_submission.rejected_by:
            return web.json_response(
                {"errors": {"": "That map was already rejected!"}},
                status=http.HTTPStatus.BAD_REQUEST,
            )
        elif prev_submission.submitter != int(submitter):
            return web.json_response(
                {"errors": {"": "Someone else already submitted this map!"}},
                status=http.HTTPStatus.FORBIDDEN,
            )
    return prev_submission
