import asyncio
import http
from aiohttp import web
import src.utils.routedecos
from src.utils.validators import validate_map_submission, check_prev_map_submission
from src.requests import ninja_kiwi_api
from config import MEDIA_BASE_URL
from src.utils.embeds import get_mapsubm_embed, send_map_submission_wh, update_map_submission_wh
from src.db.queries.mapsubmissions import add_map_submission, get_map_submissions_by_message, reject_submission
from src.utils.files import save_image
from src.exceptions import ValidationException, MissingPermsException, GenericErrorException


@src.utils.routedecos.check_bot_signature(files=["proof_completion"])
@src.utils.routedecos.require_perms()
async def post(
        _r: web.Request,
        json_data: dict = None,
        permissions: "src.db.models.Permissions" = None,
        files: list[tuple[str, bytes] | None] = None,
        **_kwargs,
) -> web.Response:
    if not permissions.has_in_any("create:map_submission"):
        raise MissingPermsException("create:map_submission")

    await validate_map_submission(json_data, has_proof=len(files) != 0)

    if (btd6_map := await ninja_kiwi_api().get_btd6_map(json_data["code"])) is None:
        raise ValidationException({"code": "That map doesn't exist"})

    embeds = await get_mapsubm_embed(json_data, json_data["user"], btd6_map)

    proof_fname = None
    if files[0]:
        proof_fname, _fp = await save_image(files[0][1], files[0][0].split(".")[-1])
        embeds[0]["image"] = {"url": f"{MEDIA_BASE_URL}/{proof_fname}"}
    wh_data = {"embeds": embeds}

    prev_submission = await check_prev_map_submission(json_data["code"], json_data["format"], json_data["user"]["id"])
    submission_id = await add_map_submission(
        json_data["code"],
        json_data["user"]["id"],
        json_data["notes"],
        json_data["format"],
        json_data["proposed"],
        f"{MEDIA_BASE_URL}/{proof_fname}" if proof_fname else None,
        edit=(prev_submission is not None),
    )

    asyncio.create_task(
        send_map_submission_wh(prev_submission, json_data["format"], submission_id, wh_data)
    )
    return web.Response(status=http.HTTPStatus.CREATED)


@src.utils.routedecos.check_bot_signature()
@src.utils.routedecos.require_perms()
async def delete(
        _r: web.Request,
        json_data: dict = None,
        permissions: "src.db.models.Permissions" = None,
        **_kwargs,
) -> web.Response:
    if "message_id" not in json_data:
        raise ValidationException({"message_id": "Missing field"})
    elif not json_data["message_id"].isnumeric():
        raise ValidationException({"message_id": "Missing field"})
    resource = await get_map_submissions_by_message(json_data["message_id"])
    if resource is None:
        return web.Response(status=http.HTTPStatus.NOT_FOUND)

    if resource.rejected_by is not None:
        raise GenericErrorException("This map was already rejected!")

    if not permissions.has("delete:map_submission", resource.format_id):
        raise MissingPermsException("delete:map_submission", resource.format_id)

    await reject_submission(resource.code, resource.format_id, json_data["user"]["id"])
    asyncio.create_task(update_map_submission_wh(resource, fail=True))
    return web.Response(status=http.HTTPStatus.NO_CONTENT)
