import io
import aiohttp.hdrs
from aiohttp import web, FormData
import json
import src.http
from http import HTTPStatus
import src.utils.routedecos
from src.utils.validators import validate_completion_submission
from src.utils.emojis import Emj
from src.db.queries.maps import get_map
from config import WEBHOOK_LIST_RUN, WEBHOOK_EXPLIST_RUN


formats = [
    {"emoji": Emj.curver, "name": "Current"},
    {"emoji": Emj.allver, "name": "Current"},
    {"emoji": Emj.experts, "name": "Expert List"},
]


@src.utils.routedecos.bearer_auth
@src.utils.routedecos.validate_resource_exists(get_map, "code", partial=True)
@src.utils.routedecos.with_discord_profile
async def post(
        request: web.Request,
        discord_profile: dict = None,
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
    reader = await request.multipart()

    embeds = []
    hook_url = ""
    images = []
    description = None
    proof_ext = None
    while part := await reader.next():
        if part.name == "proof_completion":
            # Max 2MB cause of the Application init
            proof_ext = part.headers[aiohttp.hdrs.CONTENT_TYPE].split("/")[-1]
            images.append((f"proof.{proof_ext}", io.BytesIO(await part.read(decode=False))))
        elif part.name == "data":
            data = await part.json()
            if len(errors := await validate_completion_submission(data)):
                return web.json_response({"errors": errors}, status=HTTPStatus.BAD_REQUEST)

            embeds = [
                {
                    "title": f"{resource.name}",
                    #  "url": f"https://join.btd6.com/Map/{resource.code}",  URL to run acceptance
                    "author": {
                        "name": discord_profile["username"],
                        "icon_url": f"https://cdn.discordapp.com/avatars/{discord_profile['id']}/{discord_profile['avatar']}",
                    },
                    "fields": [
                        {
                            "name": "Format",
                            "value": f"{formats[data['format']-1]['emoji']} {formats[data['format']-1]['name']}",
                            "inline": True,
                        },
                    ],
                    "color": 0x2e7d32 if 0 < data["format"] <= 2 else 0x7b1fa2
                },
            ]
            if data["notes"]:
                embeds[0]["description"] = data["notes"]
            if data["no_geraldo"] or data["current_lcc"] or data["black_border"]:
                embeds[0]["fields"].append({
                    "name": "Run Properties",
                    "value": (f"* {Emj.black_border} Black Border\n" if data["black_border"] else "") +
                            (f"* {Emj.no_geraldo} No Optimal Hero\n" if data["no_geraldo"] else "") +
                            (f"* {Emj.lcc} Least Cash CHIMPS\n" if data["current_lcc"] else ""),
                    "inline": True,
                })
                description = f"__Video Proof: {data['video_proof_url']}__"
            hook_url = WEBHOOK_LIST_RUN if 0 < data["format"] <= 2 else WEBHOOK_EXPLIST_RUN

    if not (len(embeds) and len(images)):
        return web.json_response(status=HTTPStatus.BAD_REQUEST)

    embeds[0]["image"] = {"url": f"attachment://proof.{proof_ext}"}

    form_data = FormData()
    json_data = {"embeds": embeds}
    if description:
        json_data["content"] = description
    form_data.add_field("payload_json", json.dumps(json_data))
    for i, value in enumerate(images):
        fname, fstream = value
        form_data.add_field(
            f"files[{i}]",
            fstream,
            filename=fname,
            content_type="application/octet-stream",
        )
    resp = await src.http.http.post(hook_url, data=form_data)

    return web.Response(status=resp.status)
