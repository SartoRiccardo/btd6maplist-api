import asyncio
import http
from aiohttp import web
from http import HTTPStatus
import src.utils.routedecos
from src.utils.validators import validate_map_submission, check_prev_map_submission
from src.requests import ninja_kiwi_api
from config import MEDIA_BASE_URL
from src.utils.embeds import get_mapsubm_embed, send_map_submission_wh
from src.db.queries.mapsubmissions import add_map_submission
from src.utils.files import save_image
from src.exceptions import ValidationException


@src.utils.routedecos.check_bot_signature(files=["proof_completion"])
@src.utils.routedecos.require_perms(throw_on_permless=False)
async def post(
        _r: web.Request,
        json_data: dict = None,
        permissions: "src.db.models.Permissions" = None,
        files: list[tuple[str, bytes] | None] = None,
        **_kwargs,
) -> web.Response:
    if not permissions.has_in_any("create:map_submission"):
        return web.json_response(
            {"errors": {"": "You are banned from submitting maps"}},
            status=http.HTTPStatus.FORBIDDEN,
        )

    await validate_map_submission(json_data)

    if (btd6_map := await ninja_kiwi_api().get_btd6_map(json_data["code"])) is None:
        raise ValidationException({"code": "That map doesn't exist"})

    proof_fname, _fp = await save_image(files[0][1], files[0][0].split(".")[-1])
    embeds = await get_mapsubm_embed(json_data, json_data["user"], btd6_map)

    embeds[0]["image"] = {"url": f"{MEDIA_BASE_URL}/{proof_fname}"}
    wh_data = {"embeds": embeds}

    prev_submission = await check_prev_map_submission(json_data["code"], json_data["format"], json_data["user"]["id"])
    await add_map_submission(
        json_data["code"],
        json_data["user"]["id"],
        json_data["notes"],
        json_data["format"],
        json_data["proposed"],
        f"{MEDIA_BASE_URL}/{proof_fname}",
        edit=(prev_submission is not None),
    )

    asyncio.create_task(
        send_map_submission_wh(prev_submission, json_data["format"], json_data["code"], wh_data)
    )
    return web.Response(status=http.HTTPStatus.CREATED)
