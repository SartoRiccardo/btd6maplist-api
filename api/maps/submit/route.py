import asyncio
import math
import http
import aiohttp.hdrs
from aiohttp import web
from src.utils.files import save_media
from http import HTTPStatus
import src.utils.routedecos
from src.utils.validators import validate_submission, check_prev_map_submission
from src.ninjakiwi import get_btd6_map
from config import WEBHOOK_LIST_SUBM, WEBHOOK_EXPLIST_SUBM, MAPLIST_BANNED_ID, MEDIA_BASE_URL
from src.utils.embeds import (
    get_mapsubm_embed,
    propositions,
    send_map_submission_webhook,
    delete_map_submission_webhook,
)
from src.utils.misc import list_to_int
from src.db.queries.mapsubmissions import (
    add_map_submission,
    get_map_submissions,
    get_map_submission,
)

PAGE_ENTRIES = 50


@src.utils.routedecos.bearer_auth
@src.utils.routedecos.with_maplist_profile
@src.utils.routedecos.register_user
async def post(
        request: web.Request,
        maplist_profile: dict,
        **_kwargs
) -> web.Response:
    """
    ---
    description: Submits a map to the maplist. Currently all this does its be a proxy for a Discord webhook.
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
              code:
                type: string
                description: The code of the map.
              notes:
                type: string
                description: Additional notes about the map.
                nullable: true
              type:
                type: string
                enum:
                - list
                - experts
                description: Which list the map will be submitted on
              proposed:
                type: integer
                description: The proposed difficulty/index of the list. 0-6 for list and 0-6 for experts.
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
            status=http.HTTPStatus.UNAUTHORIZED,
        )

    discord_profile = maplist_profile["user"]

    embeds = []
    data = None
    hook_url = ""
    proof_fname = None

    reader = await request.multipart()
    while part := await reader.next():
        if part.name == "proof_completion":
            proof_ext = part.headers[aiohttp.hdrs.CONTENT_TYPE].split("/")[-1]
            file_contents = await part.read(decode=False)
            proof_fname, _fpath = await save_media(file_contents, proof_ext)
        elif part.name == "data":
            data = await part.json()
            if len(errors := await validate_submission(data)):
                return web.json_response({"errors": errors}, status=HTTPStatus.BAD_REQUEST)
            if not data["proposed"] in range(len(propositions[data["type"]])):
                return web.json_response({"errors": {"proposition": "Out of range"}}, status=HTTPStatus.BAD_REQUEST)

            if not (btd6_map := await get_btd6_map(data["code"])):
                return web.json_response({"errors": {"code": "That map doesn't exist"}}, status=HTTPStatus.BAD_REQUEST)

            embeds = get_mapsubm_embed(data, discord_profile, btd6_map)
            hook_url = WEBHOOK_LIST_SUBM if data["type"] == "list" else WEBHOOK_EXPLIST_SUBM

    if len(embeds) == 0 or data is None or proof_fname is None:
        return web.json_response(status=HTTPStatus.BAD_REQUEST)

    embeds[0]["image"] = {"url": f"{MEDIA_BASE_URL}/{proof_fname}"}
    wh_data = {"embeds": embeds}

    prev_submission = await check_prev_map_submission(data["code"], maplist_profile["user"]["id"])
    if isinstance(prev_submission, web.Response):
        return prev_submission

    await add_map_submission(
        data["code"],
        maplist_profile["user"]["id"],
        data["notes"],
        list_to_int.index(data["type"]),
        data["proposed"],
        f"{MEDIA_BASE_URL}/{proof_fname}",
        edit=(prev_submission is not None),
    )

    async def update_wh():
        if prev_submission and prev_submission.wh_data:
            old_hook_url = WEBHOOK_LIST_SUBM if prev_submission.for_list == 0 else WEBHOOK_EXPLIST_SUBM
            await delete_map_submission_webhook(old_hook_url, prev_submission.wh_data.split(";")[0])
        await send_map_submission_webhook(hook_url, data["code"], wh_data)

    asyncio.create_task(update_wh())
    return web.Response(status=http.HTTPStatus.NO_CONTENT)


async def get(request: web.Request) -> web.Response:
    """
    ---
    description: Gets all map submissions.
    tags:
    - The List
    - Expert List
    parameters:
    - in: query
      name: page
      required: false
      schema:
        type: integer
      description: Pagination. Defaults to `1`.
    - in: query
      name: omit_rejected
      required: false
      schema:
        type: boolean
      description: Whether to omit rejected completions or not.
    responses:
      "200":
        description: A list of map submissions.
        content:
          application/json:
            schema:
              type: object
              properties:
                total:
                  type: integer
                  description: The total count of player entries.
                pages:
                  type: integer
                  description: The total number of pages.
                completions:
                  type: array
                  items:
                    $ref: "#/components/schemas/MapSubmission"
    """
    page = request.query.get("page", "1")
    page = max(1, int(page if page.isnumeric() else "1"))

    show = request.query.get("pending", "pending").lower()
    if show not in ["pending", "all"]:
        show = "pending"

    total, submissions = await get_map_submissions(
        omit_rejected=(show == "pending"),
        idx_start=PAGE_ENTRIES * (page - 1),
        amount=PAGE_ENTRIES,
    )
    return web.json_response({
        "total": total,
        "pages": math.ceil(total/PAGE_ENTRIES),
        "submissions": [sub.to_dict() for sub in submissions],
    })
