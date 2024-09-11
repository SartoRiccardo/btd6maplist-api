import io
import aiohttp.hdrs
from aiohttp import web, FormData
import json
import src.http
from http import HTTPStatus
import src.utils.routedecos
from src.utils.validators import validate_submission
from src.ninjakiwi import get_btd6_map
from config import WEBHOOK_LIST_SUBM, WEBHOOK_EXPLIST_SUBM


propositions = {
    "list": ["Top 3", "Top 10", "#11 ~ 20", "#21 ~ 30", "#31 ~ 40", "#41 ~ 50"],
    "experts": ["Casual", "Casual/Medium", "Medium", "Medium/Hard", "Hard", "Hard/True", "True"],
}


@src.utils.routedecos.bearer_auth
@src.utils.routedecos.with_discord_profile
@src.utils.routedecos.register_user
async def post(request: web.Request, discord_profile: dict, **_kwargs) -> web.Response:
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
    embeds = []
    hook_url = ""
    images = []
    proof_ext = None

    reader = await request.multipart()
    while part := await reader.next():
        if part.name == "proof_completion":
            # Max 2MB cause of the Application init
            proof_ext = part.headers[aiohttp.hdrs.CONTENT_TYPE].split("/")[-1]
            images.append((f"proof.{proof_ext}", io.BytesIO(await part.read(decode=False))))
        elif part.name == "data":
            data = await part.json()
            if len(errors := await validate_submission(data)):
                return web.json_response({"errors": errors}, status=HTTPStatus.BAD_REQUEST)
            if not data["proposed"] in range(len(propositions[data["type"]])):
                return web.json_response({"errors": {"proposition": "Out of range"}}, status=HTTPStatus.BAD_REQUEST)

            if not (btd6_map := await get_btd6_map(data["code"])):
                return web.json_response({"errors": {"code": "That map doesn't exist"}}, status=HTTPStatus.BAD_REQUEST)

            # Doesn't work for some reason so upload manually
            preview = await src.http.http.get(f"https://data.ninjakiwi.com/btd6/maps/map/{data['code']}/preview")
            if preview.ok:
                images.append(("preview.png", io.BytesIO(await preview.read())))

            embeds = embed_from_json(data, discord_profile, btd6_map)
            hook_url = WEBHOOK_LIST_SUBM if data["type"] == "list" else WEBHOOK_EXPLIST_SUBM

    if not (len(embeds) and len(images)):
        return web.json_response(status=HTTPStatus.BAD_REQUEST)

    embeds[0]["image"] = {"url": f"attachment://proof.{proof_ext}"}

    form_data = FormData()
    json_data = {"embeds": embeds}
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


def embed_from_json(
        data: dict,
        discord_profile: dict,
        btd6_map: dict,
) -> list[dict]:
    embeds = [
        {
            "title": f"{btd6_map['name']} - {data['code']}",
            "url": f"https://join.btd6.com/Map/{data['code']}",
            "author": {
                "name": discord_profile["username"],
                "icon_url": f"https://cdn.discordapp.com/avatars/{discord_profile['id']}/{discord_profile['avatar']}",
            },
            "fields": [
                {
                    "name": f"Proposed {'List Position' if data['type'] == 'list' else 'Difficulty'}",
                    "value":
                        propositions[data["type"]][data["proposed"]]
                        if data['type'] == 'list' else
                        (propositions[data['type']][data["proposed"]] + " Expert"),
                },
            ],
            "color": 0x2e7d32 if data["type"] == "list" else 0x7b1fa2
        },
        {
            "url": f"https://join.btd6.com/Map/{data['code']}",
            "image": {
                # "url": f"https://data.ninjakiwi.com/btd6/maps/map/{data['code']}/preview",
                "url": "attachment://preview.png"
            },
        }
    ]
    if data["notes"]:
        embeds[0]["description"] = data["notes"]
    return embeds
