from aiohttp import web, FormData
import json
import src.http
from http import HTTPStatus
import src.utils.routedecos
from src.utils.files import save_media
from src.utils.validators import validate_completion_submission
from src.db.queries.maps import get_map
from src.db.queries.completions import submit_run
from config import WEBHOOK_LIST_RUN, WEBHOOK_EXPLIST_RUN, MEDIA_BASE_URL
from src.utils.embeds import get_runsubm_embed


@src.utils.routedecos.check_bot_signature(files=["proof_completion"], path_params=["code"])
@src.utils.routedecos.validate_resource_exists(get_map, "code", partial=True)
async def post(
        _r: web.Request,
        files: list[tuple[str, bytes] | None] = None,
        json_data: dict = None,
        resource: "src.db.models.PartialMap" = None,
        **_kwargs
) -> web.Response:
    if len(errors := await validate_completion_submission(json_data)):
        return web.json_response({"errors": errors}, status=HTTPStatus.BAD_REQUEST)
    if resource.difficulty == -1 and json_data["format"] in range(50, 100):
        return web.json_response(
            {"errors": {"format": "Submitted experts run for non-experts map"}},
            status=HTTPStatus.BAD_REQUEST,
        )
    # if (resource.placement_cur == -1 or resource.placement_all == -1) and json_data["format"] in range(1, 50):
    #     return web.json_response(
    #         {"errors": {"format": "Submitted maplist run for non-maplist map"}},
    #         status=HTTPStatus.BAD_REQUEST,
    #     )

    discord_profile = json_data["submitter"]
    proof_fname, _fp = await save_media(files[0][1], files[0][0].split(".")[-1])

    lcc_data = None
    if json_data["current_lcc"]:
        lcc_data = {
            "proof": f"{MEDIA_BASE_URL}/{proof_fname}",
            "leftover": json_data["leftover"],
        }
    run_id = await submit_run(
        resource.code,
        json_data["black_border"],
        json_data["no_geraldo"],
        json_data["format"],
        lcc_data,  # leftover, proof
        int(discord_profile['id']),
        f"{MEDIA_BASE_URL}/{proof_fname}",
        json_data["video_proof_url"],
        json_data["notes"],
    )

    embeds = get_runsubm_embed(json_data, discord_profile, resource)
    embeds[0]["image"] = {"url": f"{MEDIA_BASE_URL}/{proof_fname}"}
    embeds[0]["footer"] = {"text": f"Run No.{run_id}"}

    msg_data = {"embeds": embeds}
    if json_data["no_geraldo"] or json_data["current_lcc"] or json_data["black_border"]:
        msg_data["content"] = f"__Video Proof: {json_data['video_proof_url']}__"

    form_data = FormData()
    form_data.add_field("payload_json", json.dumps(msg_data))

    hook_url = WEBHOOK_LIST_RUN if 0 < json_data["format"] <= 50 else WEBHOOK_EXPLIST_RUN
    resp = await src.http.http.post(hook_url, data=form_data)

    return web.Response(status=resp.status)
