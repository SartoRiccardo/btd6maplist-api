import asyncio
import validators
from aiohttp import web
import http
from typing import Type, Any, get_args, Literal
import re
import src.utils.routedecos
import src.http
from src.db.models import MapSubmission
from src.db.queries.maps import map_exists, alias_exists, get_map
from src.db.queries.users import get_user_min
from src.db.queries.format import get_format
from src.db.queries.mapsubmissions import get_map_submission
from src.db.queries.achievement_roles import get_duplicate_ds_roles
from .formats import format_idxs, FormatStatus


MAX_TEXT_LEN = 100
MAX_LONG_TEXT_LEN = 500
MAX_ADD_CODES = 5
MAX_PROOF_URL = 5
MAX_TOOLTIP_LEN = 128
MAX_ROLE_NAME_LEN = 32


async def validate_map_code(
        code: str,
        validate_code_exists: bool = True,
) -> str | None:
    if not isinstance(code, str) or not re.match("^[A-Z]{7}$", code):
        return "Must be a 7 uppercase letter code"
    elif validate_code_exists:
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
        if dict in get_args(schema):
            return {}
        if not isinstance(schema, dict):
            return {f"{path}"[1:]: "Item cannot be an object"}
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
    elif isinstance(schema, list) or \
            isinstance(schema, dict) or \
            not isinstance(body, schema):
        return {path[1:]: f"Wrong typing (must be `{schema}`)"}
    return {}


def typecheck_full_map(body: dict) -> dict:
    check_fields_exists = {
        "code": str,
        "name": str,
        "r6_start": str | None,
        "map_data": str | None,
        "additional_codes": [{"code": str, "description": str}],
        "creators": [{"id": str, "role": str | None}],
        "verifiers": [{"id": str, "version": int | None}],
        "aliases": [str],
        "version_compatibilities": [{"version": int, "status": int}],
        "optimal_heros": [str],
        "map_preview_url": str | None,
    }
    for format_id in format_idxs:
        check_fields_exists[format_idxs[format_id].key] = int | None
    check = check_fields(body, check_fields_exists)
    if len(check):
        return check


async def validate_full_map(
        body: dict,
        check_dup_code: bool = True,
        validate_code_exists: bool = True,
) -> dict:
    errors = {}
    if check_fail := typecheck_full_map(body):
        return check_fail

    if check_dup_code and await map_exists(body["code"]):
        return {"code": "Map already exists"}
    if code_err := await validate_map_code(body["code"], validate_code_exists=validate_code_exists):
        errors["code"] = code_err
    for i, addcode in enumerate(body["additional_codes"][:MAX_ADD_CODES]):
        if code_err := await validate_map_code(addcode["code"]):
            errors[f"additional_codes[{i}].code"] = code_err
        if addcode["description"] is not None:
            if len(addcode["description"]) > MAX_TEXT_LEN:
                errors[f"additional_codes[{i}].description"] = f"Must be under {MAX_TEXT_LEN} characters"
            elif len(addcode["description"]) == 0:
                errors[f"additional_codes[{i}].description"] = f"Cannot be an empty string"

    if len(body["name"]) > MAX_TEXT_LEN:
        errors["name"] = f"Must be under {MAX_TEXT_LEN} characters"
    elif len(body["name"]) == 0:
        errors["name"] = f"Must have a name"

    rep_alias_idx = get_repeated_indexes(body["aliases"])
    if len(rep_alias_idx):
        for idx in rep_alias_idx:
            errors[f"aliases[{idx}].alias"] = "Duplicate alias"
    else:
        map_res = await get_map(body["code"])

        # REFACTOR just take 1 query
        async def cannot_be_taken(a: str) -> bool:
            """Returns True if the alias cannot be taken"""
            exists = await alias_exists(a)
            if map_res is None:
                return exists
            else:
                return a not in map_res.aliases and exists
        dup_aliases = await asyncio.gather(*[
            cannot_be_taken(alias) for alias in body["aliases"]
        ])
        for i, isdup in enumerate(dup_aliases):
            if isdup:
                errors[f"aliases[{i}].alias"] = "Already assigned to another map"

    if body["r6_start"] is not None and \
            (len(body["r6_start"]) == 0 or not validators.url(body["r6_start"])):
        errors["r6_start"] = "Must be a URL"
    if body["map_preview_url"] is not None and \
            (len(body["map_preview_url"]) == 0 or not validators.url(body["map_preview_url"])):
        errors["map_preview_url"] = "Must be a URL"

    if rep_idx := get_repeated_indexes([el["id"] for el in body["creators"]]):
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
            if crt["role"] is not None:
                if len(crt["role"]) > MAX_TEXT_LEN:
                    errors[f"creators[{i}].role"] = f"Must be under {MAX_TEXT_LEN} characters"
                elif len(crt["role"]) == 0:
                    errors[f"creators[{i}].role"] = "Cannot be an empty string"

    users = await asyncio.gather(*[
        get_user_min(verif["id"]) for verif in body["verifiers"]
    ])
    for i, usr in enumerate(users):
        if usr is None:
            errors[f"verifiers[{i}].id"] = "This user doesn't exist"
        else:
            body["verifiers"][i]["id"] = str(usr.id)

    one_format_set = False
    for format_id in format_idxs:
        if body[format_idxs[format_id].key] is not None:
            one_format_set = True
            is_valid, error_msg, should_delete = await format_idxs[format_id].validate(body[format_idxs[format_id].key])
            if not is_valid:
                errors[format_idxs[format_id].key] = error_msg
            if should_delete:
                del body[format_idxs[format_id].key]
    if not one_format_set:
        for format_id in format_idxs:
            errors[format_idxs[format_id].key] = "At least one of these must be not null"

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


def typecheck_map_submission(body: dict) -> dict:
    check_fields_exists = {
        "code": str,
        "notes": str | None,
        "proposed": int,
        "format": int,
    }
    check = check_fields(body, check_fields_exists)
    if len(check):
        return check


async def validate_map_submission(body: dict) -> dict:
    if check_fail := typecheck_map_submission(body):
        return check_fail

    errors = {}

    list_format = await get_format(body["format"])
    if list_format is None:
        errors["format"] = "Format does not exist"
    elif list_format.map_submission_status == FormatStatus.CLOSED:
        errors["format"] = "Format is currently not accepting submissions"

    if await map_exists(body["code"]):
        return {"code": "Map already exists"}
    if body["notes"]:
        if len(body["notes"]) > MAX_LONG_TEXT_LEN:
            errors["notes"] = f"Must be under {MAX_LONG_TEXT_LEN} characters"
        if len(body["notes"]) == 0:
            body["notes"] = None
    return errors


async def validate_completion_submission(
    body: dict,
    on_map: "src.db.models.PartialMap",
) -> dict:
    check_fields_exists = {
        "format": int,
        "notes": str | None,
        "black_border": bool,
        "no_geraldo": bool,
        "current_lcc": bool,
        "video_proof_url": [str],
    }
    check = check_fields(body, check_fields_exists)
    if len(check):
        return check

    errors = {}
    if len(body["video_proof_url"]) > MAX_PROOF_URL:
        errors[f"video_proof_url"] = f"Can submit up to {MAX_PROOF_URL} URLs"
    else:
        for i, url in enumerate(body["video_proof_url"]):
            if len(url) > MAX_TEXT_LEN:
                errors[f"video_proof_url[{i}]"] = f"URLs must be long max. {MAX_TEXT_LEN} each"
            if not validators.url(url):
                errors[f"video_proof_url[{i}]"] = "Invalid video URL"

    list_format = await get_format(body["format"])
    if list_format is None:
        errors["format"] = "This format does not exist"
    elif list_format.run_submission_status == FormatStatus.CLOSED:
        errors["format"] = "This format does not accept completion submissions"
    elif list_format.run_submission_status == FormatStatus.LCC_ONLY and not body["current_lcc"]:
        errors["format"] = "This format only accepts LCC completion submissions"
        errors["current_lcc"] = "Must be true for this format"
    elif not await format_idxs[body["format"]].can_accept_run(on_map):
        errors["format"] = "This map doesn't accept completions on that format"
    else:
        requires_recording = format_idxs[body["format"]].run_requires_recording(
            on_map,
            body["black_border"],
            body["no_geraldo"],
            body["current_lcc"],
        )
        if requires_recording and len(body["video_proof_url"]) == 0:
            errors["video_proof_url"] = "Missing proof URL"
        if body["current_lcc"]:
            if "leftover" not in body or not isinstance(body["leftover"], int):
                errors["leftover"] = "Missing or non-integer saveup"
            elif 0 > body["leftover"]:
                errors["leftover"] = "Must be greater than 0"

    if body["notes"] is not None:
        if len(body["notes"]) == 0:
            errors["notes"] = "Notes cannot be an empty string"
        elif len(body["notes"]) > MAX_LONG_TEXT_LEN:
            errors["notes"] = f"Notes cannot be longer than {MAX_LONG_TEXT_LEN} characters"
    return errors


async def validate_completion(body: dict) -> dict[str, str]:
    check_fields_exists = {
        "black_border": bool,
        "no_geraldo": bool,
        "format": int,
        "user_ids": [str],
        "lcc": dict | None,
    }
    if len(check := check_fields(body, check_fields_exists)):
        return check

    errors = {}

    if body["lcc"] is not None:
        check_lcc_exists = {
            "leftover": int,
        }
        if len(check := check_fields(body["lcc"], check_lcc_exists, path=".lcc")):
            return check

        if 0 > body["lcc"]["leftover"]:
            errors["lcc.leftover"] = "Must be greater than 0"

    list_format = await get_format(body["format"])
    if list_format is None:
        errors["format"] = "Format does not exist"

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
    if len(body["name"]) == 0:
        errors["name"] = "Name cannot be blank"
    elif len(body["name"]) > MAX_TEXT_LEN:
        errors["name"] = f"Name cannot be more than {MAX_TEXT_LEN} characters long"
    elif (match := re.search(r"[^\w _\.]", body["name"])) is not None:
        errors["name"] = f"Name cannot contain the character: {match.group(0)}"

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


def validate_completion_perms(
        permissions: "src.db.models.Permissions",
        new_format: int,
        old_format: int | None = None,
        action: Literal["edit", "create", "delete"] = "create",
) -> web.Response | None:
    req_perm = f"{action}:completion"

    if not permissions.has(req_perm, new_format):
        return web.json_response(
            {"errors": {"format": f"You are missing `{req_perm}` on format `{new_format}`"}},
            status=http.HTTPStatus.FORBIDDEN,
        )

    if old_format is not None and not permissions.has(req_perm, old_format):
        return web.json_response(
            {"errors": {"format": f"You are missing `{req_perm}` on format `{old_format}`"}},
            status=http.HTTPStatus.FORBIDDEN,
        )


async def validate_achievement_roles(body: dict) -> dict:
    check_fields_exists = {
        "lb_format": int,
        "lb_type": str,
        "roles": [{
            "threshold": int,
            "for_first": bool,
            "tooltip_description": str | None,
            "name": str,
            "clr_border": int,
            "clr_inner": int,
            "linked_roles": [{"guild_id": str, "role_id": str}],
        }],
    }
    check = check_fields(body, check_fields_exists)
    if len(check):
        return check

    errors = {}
    list_format = await get_format(body["lb_format"])
    if list_format is None:
        errors["lb_format"] = "Format does not exist"
    if body["lb_type"] not in ["points", "no_geraldo", "black_border", "lccs"]:
        errors["lb_type"] = "Leaderboard type does not exist"

    has_first = False
    discord_role_idxs = {}
    for i, role in enumerate(body["roles"]):
        if role["for_first"]:
            if has_first:
                errors[f"roles[{i}].for_first"] = "Can only have one role for first place"
            has_first = True
            role["threshold"] = 0
        elif role["threshold"] <= 0:
            errors[f"roles[{i}].threshold"] = "Threshold must be positive"
        if role["tooltip_description"] is not None:
            if len(role["tooltip_description"]) == 0:
                role["tooltip_description"] = None
            elif len(role["tooltip_description"]) > MAX_TOOLTIP_LEN:
                errors[f"roles[{i}].tooltip_description"] = f"Tooltip description must be max {MAX_TOOLTIP_LEN} characters long"
        if len(role["name"]) == 0:
            errors[f"roles[{i}].name"] = f"Name cannot be blank"
        elif len(role["name"]) > MAX_ROLE_NAME_LEN:
            errors[f"roles[{i}].name"] = f"Name must be max {MAX_ROLE_NAME_LEN} characters long"
        if not (0 <= role["clr_border"] <= 0xFFFFFF):
            errors[f"roles[{i}].clr_border"] = f"Invalid color"
        if not (0 <= role["clr_inner"] <= 0xFFFFFF):
            errors[f"roles[{i}].clr_inner"] = f"Invalid color"
        for j, discord_role in enumerate(role["linked_roles"]):
            if not discord_role["guild_id"].isnumeric():
                errors[f"roles[{i}].linked_roles[{j}].guild_id"] = "Invalid Guild ID"
            if not discord_role["role_id"].isnumeric():
                errors[f"roles[{i}].linked_roles[{j}].role_id"] = "Invalid Role ID"
            else:
                role_id = int(discord_role["role_id"])
                if role_id in discord_role_idxs:
                    errors[f"roles[{i}].linked_roles[{j}].role_id"] = "Duplicate Discord role ID"
                discord_role_idxs[role_id] = (i, j)

    rep_threshold_idx = get_repeated_indexes([rl["threshold"] for rl in body["roles"]])
    if len(rep_threshold_idx):
        for idx in rep_threshold_idx:
            errors[f"roles[{idx}].threshold"] = "Duplicate threshold"

    if len(errors) == 0:
        role_dupes = await get_duplicate_ds_roles(body["lb_format"], body["lb_type"], list(discord_role_idxs.keys()))
        for dupe in role_dupes:
            i, j = discord_role_idxs[dupe]
            errors[f"roles[{i}].linked_roles[{j}].role_id"] = "This role is already used elsewhere!"

    return errors
