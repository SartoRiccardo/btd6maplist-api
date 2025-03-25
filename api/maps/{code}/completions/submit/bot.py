import http
from aiohttp import web, FormData
import asyncio
import json
import src.http
from http import HTTPStatus
import src.utils.routedecos
from src.utils.files import save_image
from src.utils.validators import validate_completion_submission
from src.utils.formats import format_idxs
from src.db.queries.maps import get_map
from src.db.queries.misc import get_config
from src.db.queries.completions import submit_run
from config import MEDIA_BASE_URL, WEB_BASE_URL
from src.utils.embeds import get_runsubm_embed, send_run_webhook

MAX_FILES = 4
compl_files = [f"proof_completion[{n}]" for n in range(MAX_FILES)]


@src.utils.routedecos.check_bot_signature(files=compl_files, path_params=["code"])
@src.utils.routedecos.require_perms(throw_on_permless=False)
@src.utils.routedecos.validate_resource_exists(get_map, "code", partial=True)
async def post(
        _r: web.Request,
        files: list[tuple[str, bytes] | None] = None,
        json_data: dict = None,
        resource: "src.db.models.PartialMap" = None,
        permissions: "src.db.models.Permissions" = None,
        **_kwargs
) -> web.Response:
    if not permissions.has_in_any("create:map_submission"):
        return web.json_response(
            {"errors": {"": "You are banned from submitting maps"}},
            status=http.HTTPStatus.FORBIDDEN,
        )

    if len(errors := await validate_completion_submission(json_data, resource)):
        return web.json_response({"errors": errors}, status=HTTPStatus.BAD_REQUEST)
    if getattr(resource, format_idxs[json_data["format"]].key) is None:
        return web.json_response(
            {"errors": {"format": "That map does not accept completions for that format"}},
            status=HTTPStatus.BAD_REQUEST,
        )

    if not permissions.has_in_any("create:completion_submission"):
        return web.json_response(
            {"errors": {"": "You are banned from submitting completions"}},
            status=http.HTTPStatus.FORBIDDEN,
        )
        # TODO Remove images inserted in this request
    elif permissions.has("require:completion_submission:recording", json_data["format"]) \
            and len(json_data["video_proof_url"]) == 0:
        return web.json_response(
            {"errors": {"video_proof_url": "You must submit a recording"}},
            status=http.HTTPStatus.BAD_REQUEST,
        )

    discord_profile = json_data["user"]
    proofs_finfo = await asyncio.gather(*[
        save_image(file[1], file[0].split(".")[-1])
        for file in files
        if file is not None
    ])

    lcc_data = None
    if json_data["current_lcc"]:
        lcc_data = {
            "proof": f"{MEDIA_BASE_URL}/{proofs_finfo[0]}",
            "leftover": json_data["leftover"],
        }

    proof_urls = [f"{MEDIA_BASE_URL}/{fname}" for fname, _fp in proofs_finfo]
    run_id = await submit_run(
        resource.code,
        json_data["black_border"],
        json_data["no_geraldo"],
        json_data["format"],
        lcc_data,  # leftover
        int(discord_profile["id"]),
        proof_urls,
        json_data["video_proof_url"],
        json_data["notes"],
    )

    embeds = await get_runsubm_embed(json_data, discord_profile, resource)
    embeds[0]["url"] = f"{WEB_BASE_URL}/completions/{run_id}"
    embeds[0]["image"] = {"url": proof_urls[0]}
    embeds[0]["footer"] = {"text": f"Run No.{run_id}"}
    for i in range(1, len(proof_urls)):
        embeds.append({
            "url": embeds[0]["url"],
            "image": {"url": proof_urls[i]},
        })

    msg_data = {"embeds": embeds}

    form_data = FormData()
    payload_json = json.dumps(msg_data)
    form_data.add_field("payload_json", payload_json)

    asyncio.create_task(
        send_run_webhook(run_id, json_data["format"], form_data, payload_json)
    )

    return web.Response(
        status=http.HTTPStatus.CREATED,
        headers={"Location": f"/completions/{run_id}"}
    )
