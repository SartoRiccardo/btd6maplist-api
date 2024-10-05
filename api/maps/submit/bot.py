import asyncio
import http
from aiohttp import web, FormData
import json
import src.http
from http import HTTPStatus
import src.utils.routedecos
from src.utils.validators import validate_submission
from src.ninjakiwi import get_btd6_map
from config import WEBHOOK_LIST_SUBM, WEBHOOK_EXPLIST_SUBM, MEDIA_BASE_URL
from src.utils.embeds import get_mapsubm_embed
from src.utils.misc import list_to_int
from src.db.queries.mapsubmissions import add_map_submission, add_map_submission_wh


@src.utils.routedecos.check_bot_signature(files=["proof_completion"])
async def post(
        _r: web.Request,
        json_data: dict = None,
        files: list[tuple[str, bytes] | None] = None,
) -> web.Response:
    if len(errors := await validate_submission(json_data)):
        return web.json_response({"errors": errors}, status=HTTPStatus.BAD_REQUEST)

    if not (btd6_map := await get_btd6_map(json_data["code"])):
        return web.json_response({"errors": {"code": "That map doesn't exist"}}, status=HTTPStatus.BAD_REQUEST)

    hook_url = WEBHOOK_LIST_SUBM if json_data["type"] == "list" else WEBHOOK_EXPLIST_SUBM
    embeds = get_mapsubm_embed(json_data, json_data["submitter"], btd6_map)

    embeds[0]["image"] = {"url": f"attachment://{files[0][0]}"}

    form_data = FormData()
    wh_data = {"embeds": embeds}
    wh_data_str = json.dumps(wh_data)
    form_data.add_field("payload_json", wh_data_str)

    async def send_webhook():
        async with src.http.http.post(hook_url + "?wait=true", data=form_data) as resp:
            msg_id = (await resp.json())["id"]
            await add_map_submission_wh(json_data["code"], f"{msg_id};{wh_data_str}")

    await add_map_submission(
        json_data["code"],
        json_data["submitter"]["id"],
        json_data["notes"],
        list_to_int.index(json_data["type"]),
        json_data["proposed"],
        f"{MEDIA_BASE_URL}/{files[0][0]}",
    )
    asyncio.create_task(send_webhook())
    return web.Response(status=http.HTTPStatus.NO_CONTENT)
