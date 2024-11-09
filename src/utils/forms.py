from aiohttp import web
import aiohttp
import http
from src.utils.validators import validate_completion, validate_full_map
from src.utils.files import save_media
from config import MEDIA_BASE_URL


async def get_completion_request(
        request: web.Request,
        user_id: str,
        is_maplist_mod: bool = False,
        is_explist_mod: bool = False,
        resource: "src.db.models.ListCompletion" = None,
) -> dict | web.Response:
    if resource and int(user_id) in [x if isinstance(x, int) else x.id for x in resource.user_ids]:
        return web.json_response(
            {"errors": {"": "Cannot edit or accept your own completion"}},
            status=http.HTTPStatus.FORBIDDEN
        )

    async def validate_json_part(data: dict) -> web.Response | None:
        if len(errors := await validate_completion(data)):
            return web.json_response({"errors": errors}, status=http.HTTPStatus.BAD_REQUEST)

        if not is_maplist_mod and (
                1 <= data["format"] <= 50 or
                resource and 1 <= resource.format <= 50):
            return web.json_response(
                {"errors": {"format": "You must be a Maplist Moderator"}},
                status=http.HTTPStatus.FORBIDDEN,
            )

        if not is_explist_mod and (
                50 <= data["format"] <= 100 or
                resource and 51 <= resource.format <= 100
        ):
            return web.json_response(
                {"errors": {"format": "You must be an Expert List Moderator"}},
                status=http.HTTPStatus.FORBIDDEN,
            )

        if user_id in data["user_ids"]:
            return web.json_response(
                {"errors": {"": "Cannot edit or accept your own completion"}},
                status=http.HTTPStatus.FORBIDDEN,
            )

    subm_proof = None
    data = None

    if request.content_type.startswith("multipart/"):
        reader = await request.multipart()
        while part := await reader.next():
            if part.name == "submission_proof":
                ext = part.headers[aiohttp.hdrs.CONTENT_TYPE].split("/")[-1]
                proof_fname, _fp = await save_media(await part.read(decode=False), ext)
                subm_proof = f"{MEDIA_BASE_URL}/{proof_fname}"

            elif part.name == "data":
                data = await part.json()
                if (response := await validate_json_part(data)) is not None:
                    return response
    elif request.content_type == "application/json":
        data = await request.json()
        if (response := await validate_json_part(data)) is not None:
            return response

    data["subm_proof"] = subm_proof

    return data


async def get_map_form(
        request: web.Request,
        editing: bool = False,
        check_dup_code: bool = False,
) -> dict | web.Response:
    async def validate_json_data(body) -> web.Response | None:
        valid_errors = await validate_full_map(
            body,
            check_dup_code=check_dup_code,
            validate_code_exists=not editing,
        )
        if len(valid_errors):
            return web.json_response(
                {"errors": valid_errors},
                status=http.HTTPStatus.BAD_REQUEST
            )
        if body["map_preview_url"] and body["map_preview_url"].startswith("https://data.ninjakiwi.com"):
            body["map_preview_url"] = None

    data = None
    files = {"r6_start": None, "map_preview_url": None}

    if request.content_type.startswith("multipart/"):
        reader = await request.multipart()
        while part := await reader.next():
            if part.name in files:
                proof_ext = "png"
                if aiohttp.hdrs.CONTENT_TYPE in part.headers:
                    proof_ext = part.headers[aiohttp.hdrs.CONTENT_TYPE].split("/")[-1]
                fname, _fpath = await save_media(await part.read(decode=False), proof_ext)
                files[part.name] = f"{MEDIA_BASE_URL}/{fname}"

            elif part.name == "data":
                data = await part.json()
                if (error_response := await validate_json_data(data)) is not None:
                    return error_response
    elif request.content_type == "application/json":
        data = await request.json()
        if (error_response := await validate_json_data(data)) is not None:
            return error_response
    else:
        return web.json_response(
            {"errors": {"": "Unsupported Content-Type. Must be application/json or multipart/*"}},
            status=http.HTTPStatus.BAD_REQUEST,
        )

    for fname in files:
        if data.get(fname, None) is None:
            data[fname] = files[fname]

    return data
