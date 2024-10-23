import asyncio
import http
from aiohttp import web
from http import HTTPStatus
import src.utils.routedecos
from src.utils.validators import validate_submission, check_prev_map_submission
from src.requests import ninja_kiwi_api
from config import WEBHOOK_LIST_SUBM, WEBHOOK_EXPLIST_SUBM, MEDIA_BASE_URL
from src.utils.embeds import get_mapsubm_embed, send_map_submission_webhook, delete_map_submission_webhook
from src.utils.misc import list_to_int
from src.db.queries.mapsubmissions import add_map_submission
from src.utils.files import save_media


@src.utils.routedecos.check_bot_signature(files=["proof_completion"])
async def post(
        _r: web.Request,
        json_data: dict = None,
        files: list[tuple[str, bytes] | None] = None,
) -> web.Response:
    if len(errors := await validate_submission(json_data)):
        return web.json_response({"errors": errors}, status=HTTPStatus.BAD_REQUEST)

    if not (btd6_map := await ninja_kiwi_api().get_btd6_map(json_data["code"])):
        return web.json_response({"errors": {"code": "That map doesn't exist"}}, status=HTTPStatus.BAD_REQUEST)

    proof_fname, _fp = await save_media(files[0][1], files[0][0].split(".")[-1])
    hook_url = WEBHOOK_LIST_SUBM if json_data["type"] == "list" else WEBHOOK_EXPLIST_SUBM
    embeds = get_mapsubm_embed(json_data, json_data["submitter"], btd6_map)

    embeds[0]["image"] = {"url": f"{MEDIA_BASE_URL}/{proof_fname}"}
    wh_data = {"embeds": embeds}

    prev_submission = await check_prev_map_submission(json_data["code"], json_data["submitter"]["id"])
    if isinstance(prev_submission, web.Response):
        return prev_submission

    await add_map_submission(
        json_data["code"],
        json_data["submitter"]["id"],
        json_data["notes"],
        list_to_int.index(json_data["type"]),
        json_data["proposed"],
        f"{MEDIA_BASE_URL}/{proof_fname}",
        edit=(prev_submission is not None),
    )

    async def update_wh():
        if prev_submission and prev_submission.wh_data:
            old_hook_url = WEBHOOK_LIST_SUBM if prev_submission.for_list == 0 else WEBHOOK_EXPLIST_SUBM
            await delete_map_submission_webhook(old_hook_url, prev_submission.wh_data.split(";")[0])
        await send_map_submission_webhook(hook_url, json_data["code"], wh_data)

    asyncio.create_task(update_wh())
    return web.Response(status=http.HTTPStatus.NO_CONTENT)
