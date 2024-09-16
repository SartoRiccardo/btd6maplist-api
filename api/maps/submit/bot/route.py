import io
from aiohttp import web, FormData
import json
import src.http
from http import HTTPStatus
import src.utils.routedecos
from src.utils.validators import validate_submission
from src.ninjakiwi import get_btd6_map
from config import WEBHOOK_LIST_SUBM, WEBHOOK_EXPLIST_SUBM
from src.utils.embeds import get_mapsubm_embed


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
    form_data.add_field("payload_json", json.dumps(wh_data))
    for i, value in enumerate(files):
        fname, fstream = value
        form_data.add_field(
            f"files[{i}]",
            io.BytesIO(fstream),
            filename=fname,
            content_type="application/octet-stream",
        )
    resp = await src.http.http.post(hook_url, data=form_data)

    return web.Response(status=resp.status)
