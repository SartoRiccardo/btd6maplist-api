import asyncio
import math
import http
import aiohttp.hdrs
from aiohttp import web
from src.utils.files import save_image
import src.utils.routedecos
from src.utils.validators import validate_map_submission, check_prev_map_submission
from src.requests import ninja_kiwi_api
from config import MEDIA_BASE_URL
from src.utils.embeds import (
    get_mapsubm_embed,
    send_map_submission_wh,
)
from src.db.queries.mapsubmissions import (
    add_map_submission,
    get_map_submissions,
)
from src.utils.formats.formatinfo import format_info
from src.exceptions import MissingPermsException, ValidationException, GenericErrorException

PAGE_ENTRIES = 50


@src.utils.routedecos.bearer_auth
@src.utils.routedecos.with_discord_profile
@src.utils.routedecos.register_user
@src.utils.routedecos.require_perms(throw_on_permless=False)
async def post(
        request: web.Request,
        discord_profile: dict = None,
        permissions: "src.db.models.Permissions" = None,
        **_kwargs
) -> web.Response:
    """
    ---
    description: Submits a map to the maplist. Must have create:map_submission
    tags:
    - Submissions
    requestBody:
      required: true
      content:
        multipart/form-data:
          schema:
            type: object
            required: [data, proof_completion]
            properties:
              data:
                type: object
                properties:
                  code:
                    type: string
                    description: The code of the map.
                  notes:
                    type: string
                    description: Additional notes about the map.
                    nullable: true
                  format:
                    $ref: "#/components/schemas/MaplistFormat"
                  proposed:
                    type: integer
                    description: The proposed difficulty/index of the list. 0-6 for list and 0-6 for experts.
              proof_completion:
                type: string
                format: binary
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
    if not permissions.has_in_any("create:map_submission"):
        return web.json_response(
            {"errors": {"": "You are banned from submitting maps"}},
            status=http.HTTPStatus.FORBIDDEN,
        )

    if not request.content_type.startswith("multipart"):
        return web.json_response(
            {"errors": {"": "multipart/* Content-Type expected"}},
            status=http.HTTPStatus.BAD_REQUEST,
        )

    embeds = []
    data = None
    proof_fname = None

    reader = await request.multipart()
    while part := await reader.next():
        if part.name == "proof_completion":
            proof_ext = part.headers[aiohttp.hdrs.CONTENT_TYPE].split("/")[-1]
            file_contents = await part.read(decode=False)
            proof_fname, _fpath = await save_image(file_contents, proof_ext)
        elif part.name == "data":
            data = await part.json()
            await validate_map_submission(data)
            
            if not permissions.has("create:map_submission", data["format"]):
                raise MissingPermsException("create:map_submission", data["format"])
            proposed_values = format_info[data["format"]].proposed_values
            if isinstance(proposed_values, tuple) and data["proposed"] not in range(len(proposed_values[1])) or \
                    not isinstance(proposed_values, tuple) and not await proposed_values(data["proposed"]):
                raise ValidationException({"proposed": "Out of range"})

            if not (btd6_map := await ninja_kiwi_api().get_btd6_map(data["code"])):
                raise ValidationException({"code": "That map doesn't exist"})

            embeds = await get_mapsubm_embed(data, discord_profile, btd6_map)

    if len(embeds) == 0 or data is None or proof_fname is None:
        raise GenericErrorException("Missing either data or proof_completion")

    embeds[0]["image"] = {"url": f"{MEDIA_BASE_URL}/{proof_fname}"}
    wh_data = {"embeds": embeds}

    prev_submission = await check_prev_map_submission(data["code"], data["format"], discord_profile["id"])
    await add_map_submission(
        data["code"],
        discord_profile["id"],
        data["notes"],
        data["format"],
        data["proposed"],
        f"{MEDIA_BASE_URL}/{proof_fname}",
        edit=(prev_submission is not None),
    )

    asyncio.create_task(
        send_map_submission_wh(prev_submission, data["format"], data["code"], wh_data)
    )
    return web.Response(status=http.HTTPStatus.NO_CONTENT if prev_submission is not None else http.HTTPStatus.CREATED)


async def get(request: web.Request) -> web.Response:
    """
    ---
    description: Gets all map submissions.
    tags:
    - Submissions
    parameters:
    - in: query
      name: page
      required: false
      schema:
        type: integer
      description: Pagination. Defaults to `1`.
    - in: query
      name: pending
      required: false
      schema:
        type: string
        enum:
          - pending
          - all
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
                submissions:
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
