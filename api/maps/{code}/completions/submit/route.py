import asyncio
import http
import aiohttp.hdrs
from aiohttp import web, FormData
import json
import src.http
from http import HTTPStatus
import src.utils.routedecos
from src.utils.files import save_image
from src.utils.validators import validate_completion_submission
from src.utils.formats import format_idxs
from src.db.queries.misc import get_config
from src.db.queries.maps import get_map
from src.db.queries.completions import submit_run
from config import (
    MEDIA_BASE_URL,
    WEB_BASE_URL,
)
from src.utils.embeds import get_runsubm_embed, send_run_webhook

MAX_FILES = 4


@src.utils.routedecos.bearer_auth
@src.utils.routedecos.validate_resource_exists(get_map, "code", partial=True)
@src.utils.routedecos.with_discord_profile
@src.utils.routedecos.register_user
@src.utils.routedecos.require_perms(throw_on_permless=False)
async def post(
        request: web.Request,
        discord_profile: dict = None,
        resource: "src.db.models.PartialMap" = None,
        permissions: "src.db.models.Permissions" = None,
        **_kwargs
) -> web.Response:
    """
    ---
    description: Submits a run to the maplist. Must have create:completion_submission
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
                    description: Whether the run is an LCC attempt.
                  leftover:
                    type: integer
                    description: Leftover of your LCC attempt, if it's an LCC attempt.
                    nullable: true
                  video_proof_url:
                    type: array
                    items:
                      type: string
                    description: |
                      URL to video proofs of you beating some hard rounds.
                      Can submit up to 5 URLs. For some types of completions, you
                      must submit at least one. Refer to submission rules on the website
                      for that.
              proof_completion:
                type: array
                items:
                  type: string
                  format: binary
    responses:
      "201":
        description: The completion was submitted
      "400":
        description: One of the fields is badly formatted.
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
    if not permissions.has_in_any("create:completion_submission"):
        return web.json_response(
            {"errors": {"": "You are banned from submitting completions"}},
            status=http.HTTPStatus.FORBIDDEN,
        )

    embeds = []
    hook_url = ""
    data = None
    proof_fnames: list[str] = []

    if not request.content_type.startswith("multipart/"):
        return web.json_response(
            {"errors": {"": "Invalid Content-Type, must be multipart/form-data"}},
            status=http.HTTPStatus.BAD_REQUEST,
        )

    reader = await request.multipart()
    while part := await reader.next():
        if part.name == "proof_completion" and len(proof_fnames) < MAX_FILES:
            proof_ext = part.headers[aiohttp.hdrs.CONTENT_TYPE].split("/")[-1]
            file_contents = await part.read(decode=False)
            fname, _fpath = await save_image(file_contents, proof_ext)
            proof_fnames.append(f"{MEDIA_BASE_URL}/{fname}")

        elif part.name == "data":
            data = await part.json()
            await validate_completion_submission(data, resource)

            if not permissions.has_in_any("create:completion_submission"):
                return web.json_response(
                    {"errors": {"": "You are banned from submitting completions"}},
                    status=http.HTTPStatus.FORBIDDEN,
                )
                # TODO Remove images inserted in this request
            elif permissions.has("require:completion_submission:recording", data["format"]) and len(data["video_proof_url"]) == 0:
                return web.json_response(
                    {"errors": {"video_proof_url": "You must submit a recording"}},
                    status=http.HTTPStatus.BAD_REQUEST,
                )

            embeds = await get_runsubm_embed(data, discord_profile, resource)

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

    asyncio.create_task(send_run_webhook(run_id, data["format"], form_data, payload_json))
    return web.Response(
        status=http.HTTPStatus.CREATED,
        headers={"Location": f"/completions/{run_id}"}
    )
