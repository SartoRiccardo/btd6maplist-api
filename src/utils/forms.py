from aiohttp import web
import aiohttp
import http
from src.utils.validators import validate_completion, validate_full_map
from src.utils.files import save_media
from config import (
    MEDIA_BASE_URL,
    MAPLIST_LISTMOD_ID,
    MAPLIST_EXPMOD_ID,
    MAPLIST_ADMIN_IDS,
)


async def get_submission(
        request: web.Request,
        maplist_profile: dict,
        resource: "src.db.models.ListCompletion" = None,
) -> dict | web.Response:
    if resource and \
            int(maplist_profile["user"]["id"]) in [x if isinstance(x, int) else x.id for x in resource.user_ids]:
        return web.json_response(
            {"errors": {"": "Cannot edit or accept your own completion"}},
            status=http.HTTPStatus.UNAUTHORIZED
        )

    proof_ext = None
    file_contents = None
    subm_proof = None
    data = None

    reader = await request.multipart()
    while part := await reader.next():
        if part.name == "proof_completion":
            proof_ext = part.headers[aiohttp.hdrs.CONTENT_TYPE].split("/")[-1]
            file_contents = await part.read(decode=False)

        if part.name == "submission_proof":
            ext = part.headers[aiohttp.hdrs.CONTENT_TYPE].split("/")[-1]
            proof_fname, _fp = await save_media(await part.read(decode=False), ext)
            subm_proof = f"{MEDIA_BASE_URL}/{proof_fname}"

        elif part.name == "data":
            data = await part.json()
            if len(errors := await validate_completion(data)):
                return web.json_response({"errors": errors}, status=http.HTTPStatus.BAD_REQUEST)

            is_admin = any([role in MAPLIST_ADMIN_IDS for role in maplist_profile["roles"]])
            is_expmod = MAPLIST_EXPMOD_ID in maplist_profile["roles"]
            is_listmod = MAPLIST_LISTMOD_ID in maplist_profile["roles"]
            if not is_admin:
                if not is_listmod and (
                        1 <= data["format"] <= 50 or
                        resource and 1 <= resource.format <= 50):
                    return web.json_response(
                        {"errors": {"format": "You must be a Maplist Moderator"}},
                        status=http.HTTPStatus.UNAUTHORIZED,
                    )

                if not is_expmod and (
                        50 <= data["format"] <= 100 or
                        resource and 51 <= resource.format <= 100):
                    return web.json_response(
                        {"errors": {"format": "You must be an Expert List Moderator"}},
                        status=http.HTTPStatus.UNAUTHORIZED,
                    )

            if maplist_profile["user"]["id"] in data["user_ids"]:
                return web.json_response(
                    {"errors": {"": "Cannot edit or accept your own completion"}},
                    status=http.HTTPStatus.UNAUTHORIZED
                )

    if data["lcc"] is not None:
        if file_contents is None and "proof_completion" not in data["lcc"]:
            return web.json_response({
                "errors": {
                    "lcc.proof_url": "Must compile at least one of these two",
                    "lcc.proof_file": "Must compile at least one of these two",
                },
            }, status=http.HTTPStatus.BAD_REQUEST)

        if "proof_completion" not in data["lcc"]:
            proof_fname, fpath = await save_media(file_contents, proof_ext)
            data["lcc"]["proof"] = f"{MEDIA_BASE_URL}/{proof_fname}"
        else:
            data["lcc"]["proof"] = data["lcc"]["proof_completion"]

    data["subm_proof"] = subm_proof

    return data


async def get_map_form(
        request: web.Request,
        check_dup_code: bool = False,
) -> dict | web.Response:
    data = None
    files = {"r6_start": None, "map_preview_url": None}

    reader = await request.multipart()
    while part := await reader.next():
        # Max 2MB total cause of the Application init
        if part.name in files:
            proof_ext = "png"
            if aiohttp.hdrs.CONTENT_TYPE in part.headers:
                proof_ext = part.headers[aiohttp.hdrs.CONTENT_TYPE].split("/")[-1]
            fname, _fpath = await save_media(await part.read(decode=False), proof_ext)
            files[part.name] = f"{MEDIA_BASE_URL}/{fname}"

        elif part.name == "data":
            data = await part.json()
            if len(errors := await validate_full_map(data, check_dup_code=check_dup_code)):
                return web.json_response({"errors": errors}, status=http.HTTPStatus.BAD_REQUEST)
            if data["map_preview_url"] and data["map_preview_url"].startswith("https://data.ninjakiwi.com"):
                data["map_preview_url"] = None

    for fname in files:
        if data[fname] is None:
            data[fname] = files[fname]

    return data
