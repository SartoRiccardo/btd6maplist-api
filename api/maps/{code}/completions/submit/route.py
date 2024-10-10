import re
import asyncio
import http
import aiohttp.hdrs
from aiohttp import web, FormData
import json
import src.http
from http import HTTPStatus
import src.utils.routedecos
from src.utils.files import save_media
from src.utils.validators import validate_completion_submission
from src.db.queries.misc import get_config
from src.db.queries.maps import get_map
from src.db.queries.completions import submit_run
from config import (
    WEBHOOK_LIST_RUN,
    WEBHOOK_EXPLIST_RUN,
    MEDIA_BASE_URL,
    MAPLIST_BANNED_ID,
    MAPLIST_NEEDSREC_ID,
    WEB_BASE_URL,
)
from src.utils.embeds import get_runsubm_embed, send_webhook

MAX_FILES = 4


@src.utils.routedecos.bearer_auth
@src.utils.routedecos.validate_resource_exists(get_map, "code", partial=True)
@src.utils.routedecos.with_maplist_profile
@src.utils.routedecos.register_user
async def post(
        request: web.Request,
        maplist_profile: dict = None,
        resource: "src.db.models.PartialMap" = None,
        **_kwargs
) -> web.Response:
    """
    ---
    description: Submits a run to the maplist. Currently all this does its be a proxy for a Discord webhook.
    tags:
    - The List
    - Expert List
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              notes:
                type: string
                description: Additional notes about the run.
                nullable: true
              format:
                $ref: "#/components/schemas/MaplistFormat"
              black_border:
                type: boolean
                description: Whether the run is black bordered.
              no_geraldo:
                type: boolean
                description: If the run didn't use the optimal hero (not necessarily geraldo).
              current_lcc:
                type: boolean
                description: Whether the run is a LCC attempt.
              video_proof_url:
                type: array
                items:
                  type: string
                description: |
                  URL to video proof of you beating some hard rounds.
                  Can be omitted if not needed.
              leftover:
                type: integer
                description: |
                  Leftover of your LCC attempt.
                  Can be omitted if not needed.
                nullable: true
    responses:
      "204":
        description: The map was submitted
      "400":
        description: |
          One of the fields is badly formatted.
        content:
          application/json:
            schema:
              type: object
              properties:
                errors:
                  type: object
                  description: Each key-value pair is the key of the wrong field and a description as to why.
      "401":
        description: Your token is missing or invalid.
    """
    if MAPLIST_BANNED_ID in maplist_profile["roles"]:
        return web.json_response(
            {"errors": {"": "You are banned from submitting..."}},
            status=http.HTTPStatus.FORBIDDEN,
        )

    maplist_cfg = await get_config()
    map_count = next(cfg for cfg in maplist_cfg if cfg.name == "map_count")
    if resource.difficulty == -1 and \
            resource.placement_cur not in range(1, map_count.value + 1):
        return web.json_response(
            {"errors": {"": "That map is not on any list and is not accepting submissions!"}},
            status=http.HTTPStatus.BAD_REQUEST,
        )

    discord_profile = maplist_profile["user"]

    embeds = []
    hook_url = ""
    data = None
    proof_fnames: list[str | None] = [None for _ in range(MAX_FILES)]

    reader = await request.multipart()
    while part := await reader.next():
        if match := re.match(r"proof_completion\[(\d+)]", part.name):
            findex = int(match.group(1))
            if findex >= MAX_FILES:
                return web.json_response(
                    {"errors": {[part.name]: f"Can upload max {MAX_FILES} files, Found index {findex}"}},
                    status=HTTPStatus.BAD_REQUEST
                )
            if proof_fnames[findex] is not None:
                return web.json_response(
                    {"errors": {[part.name]: "Duplicate index"}},
                    status=HTTPStatus.BAD_REQUEST
                )

            proof_ext = part.headers[aiohttp.hdrs.CONTENT_TYPE].split("/")[-1]
            file_contents = await part.read(decode=False)
            fname, _fpath = await save_media(file_contents, proof_ext)
            proof_fnames[findex] = f"{MEDIA_BASE_URL}/{fname}"

        elif part.name == "data":
            data = await part.json()
            if len(errors := await validate_completion_submission(data)):
                return web.json_response({"errors": errors}, status=HTTPStatus.BAD_REQUEST)

            if MAPLIST_NEEDSREC_ID in maplist_profile["roles"] and "video_proof_url" not in data:
                return web.json_response(
                    {"errors": {"video_proof_url": "You must submit a recording"}},
                    status=http.HTTPStatus.UNAUTHORIZED,
                )

            embeds = get_runsubm_embed(data, discord_profile, resource)
            if resource.difficulty == -1 and data["format"] in range(50, 100):
                return web.json_response(
                    {"errors": {"format": "Submitted experts run for non-experts map"}},
                    status=HTTPStatus.BAD_REQUEST,
                )
            # if (resource.placement_cur == -1 or resource.placement_all == -1) and data["format"] in range(1, 50):
            #     return web.json_response(
            #         {"errors": {"format": "Submitted maplist run for non-maplist map"}},
            #         status=HTTPStatus.BAD_REQUEST,
            #     )
            hook_url = WEBHOOK_LIST_RUN if 0 < data["format"] <= 50 else WEBHOOK_EXPLIST_RUN

    proof_fnames = [url for url in proof_fnames if url is not None]
    if not (len(embeds) and len(proof_fnames)):
        return web.json_response(status=HTTPStatus.BAD_REQUEST)

    lcc_data = None
    if data["current_lcc"]:
        lcc_data = {
            "proof": proof_fnames[0],
            "leftover": data["leftover"],
        }

    run_id = await submit_run(
        resource.code,
        data["black_border"],
        data["no_geraldo"],
        data["format"],
        lcc_data,  # leftover, proof
        int(discord_profile['id']),
        proof_fnames,
        data["video_proof_url"],
        data["notes"],
    )

    embeds[0]["url"] = f"{WEB_BASE_URL}/completions/{run_id}"
    embeds[0]["image"] = {"url": proof_fnames[0]}
    embeds[0]["footer"] = {"text": f"Run No.{run_id}"}
    for i in range(1, len(proof_fnames)):
        embeds.append({
            "url": embeds[0]["url"],
            "image": {"url": proof_fnames[i]},
        })

    form_data = FormData()

    json_data = {"embeds": embeds}
    payload_json = json.dumps(json_data)
    form_data.add_field("payload_json", payload_json)

    asyncio.create_task(send_webhook(run_id, hook_url, form_data, payload_json))
    return web.Response(status=http.HTTPStatus.NO_CONTENT)
