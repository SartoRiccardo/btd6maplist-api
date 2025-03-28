from aiohttp import web
import aiohttp
import http
from src.utils.validators import validate_completion, validate_full_map, validate_completion_perms
from src.utils.files import save_image
from src.exceptions import ValidationException, GenericErrorException
from config import MEDIA_BASE_URL


async def get_completion_request(
        request: web.Request,
        user_id: str,
        permissions: "src.db.modes.Permissions" = None,
        resource: "src.db.models.ListCompletion" = None,
) -> dict:
    if resource and int(user_id) in [x if isinstance(x, int) else x.id for x in resource.user_ids]:
        raise GenericErrorException(
            "Cannot edit or accept your own completion",
            status_code=http.HTTPStatus.FORBIDDEN,
        )

    async def validate_json_part(data: dict) -> None:
        await validate_completion(data)

        err_resp = validate_completion_perms(
            permissions,
            data["format"],
            resource.format if resource else None,
            action="edit" if resource else "create",
        )
        if isinstance(err_resp, web.Response):
            return err_resp

        if user_id in data["user_ids"]:
            raise GenericErrorException(
                "Cannot edit or accept your own completion",
                status_code=http.HTTPStatus.FORBIDDEN,
            )

    subm_proof = None
    data = None

    if request.content_type.startswith("multipart/"):
        reader = await request.multipart()
        while part := await reader.next():
            if part.name == "submission_proof":
                ext = part.headers[aiohttp.hdrs.CONTENT_TYPE].split("/")[-1]
                proof_fname, _fp = await save_image(await part.read(decode=False), ext)
                subm_proof = f"{MEDIA_BASE_URL}/{proof_fname}"

            elif part.name == "data":
                data = await part.json()
                await validate_json_part(data)
    elif request.content_type == "application/json":
        data = await request.json()
        await validate_json_part(data)

    data["subm_proof"] = subm_proof

    return data


async def get_map_form(
        request: web.Request,
        editing: bool = False,
        check_dup_code: bool = False,
) -> dict:
    async def validate_json_data(body) -> None:
        await validate_full_map(
            body,
            check_dup_code=check_dup_code,
            validate_code_exists=not editing,
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
                fname, _fpath = await save_image(await part.read(decode=False), proof_ext)
                files[part.name] = f"{MEDIA_BASE_URL}/{fname}"

            elif part.name == "data":
                data = await part.json()
                await validate_json_data(data)
    elif request.content_type == "application/json":
        data = await request.json()
        await validate_json_data(data)
    else:
        raise GenericErrorException(
            "Unsupported Content-Type. Must be application/json or multipart/*",
            status_code=http.HTTPStatus.BAD_REQUEST,
        )

    for fname in files:
        if data.get(fname, None) is None:
            data[fname] = files[fname]

    return data
