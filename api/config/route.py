import json
import src.http
from aiohttp import web
from src.utils.misc import index_where
from src.db.queries.misc import get_config, update_config
from config import MAPLIST_GUILD_ID, MAPLIST_LISTMOD_ID, MAPLIST_EXPMOD_ID


async def get(_r: web.Request):
    """
    ---
    description: Returns a list of config variables for the project.
    tags:
    - Misc
    responses:
      "200":
        description: Returns an array of `ConfigVar`.
        content:
          application/json:
            schema:
              type: array
              items:
                $ref: "#/components/schemas/ConfigVar"
    """
    return web.json_response([cfg.to_dict() for cfg in await get_config()])


async def put(request: web.Request):
    """
    ---
    description: Change any number of the config variables. Must be a Maplist Moderator.
    tags:
    - Misc
    requestBody:
      required: true
      content:
        application/json:
          schema:
            allOf:
            - type: object
              properties:
                token:
                  type: string
                  description: A Discord OAuth2 access token.
            - type: array
              items:
                $ref: "#/components/schemas/ConfigVar"
    responses:
      "200":
        description: |
          Returns the modified config variables.
          `error` will be an empty object in this case.
        content:
          application/json:
            schema:
              type: object
              properties:
                errors:
                  type: object
                data:
                  type: array
                  items:
                    $ref: "#/components/schemas/ConfigVar"
      "400":
        description: |
          One of the fields is badly formatted.
          `data` will be an empty array in this case.
        content:
          application/json:
            schema:
              type: object
              properties:
                errors:
                  type: object
                  description: Each key-value pair is the key of the wrong field and a description as to why.
                data:
                  type: array
                  items:
                    $ref: "#/components/schemas/ConfigVar"
                  example: []
      "401":
        description: Your token is missing, invalid or you don't have the privileges for this.
    """
    data = json.loads(await request.text())

    if "token" not in data:
        return web.Response(status=401)
    if "config" not in data:
        return web.json_response({"errors": "Missing config"}, status=400)

    allowed_keys = [
        "points_top_map", "points_bottom_map", "formula_slope", "points_extra_lcc", "points_multi_gerry",
        "points_multi_bb", "decimal_digits", "map_count", "current_btd6_ver"
    ]
    for key in data["config"]:
        if key not in allowed_keys:
            return web.json_response({"error": f"Found wrong key \"{key}\""}, status=400)

    errors = {}
    config = await get_config()
    for key in data["config"]:
        idx = index_where(config, lambda x: x.name == key)
        vtype = type(config[idx].value)
        try:
            data["config"][key] = vtype(data["config"][key])
        except ValueError:
            errors[key] = f"Must be of type {vtype.__name__}"

    if len(errors):
        return web.json_response({"errors": errors, "data": {}}, status=400)

    disc_response = await src.http.http.get(
        f"https://discord.com/api/v10/users/@me/guilds/{MAPLIST_GUILD_ID}/member",
        headers={"Authorization": f"Bearer {data['token']}"}
    )
    if not disc_response.ok:
        return web.Response(status=401)

    maplist_profile = await disc_response.json()
    if MAPLIST_LISTMOD_ID not in maplist_profile["roles"]:
        return web.json_response({"error": "You are not a Maplist Moderator"}, status=401)

    await update_config(data["config"])
    return web.json_response({"errors": {}, "data": data["config"]})
