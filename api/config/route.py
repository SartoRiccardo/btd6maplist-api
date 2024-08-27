from aiohttp import web
from src.utils.misc import index_where
from src.db.queries.misc import get_config, update_config
import src.utils.routedecos
from config import MAPLIST_LISTMOD_ID#, MAPLIST_EXPMOD_ID


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


async def put_validate(body: dict) -> dict:
    if "config" not in body:
        return {"": "Missing config"}

    allowed_keys = [
        "points_top_map", "points_bottom_map", "formula_slope", "points_extra_lcc", "points_multi_gerry",
        "points_multi_bb", "decimal_digits", "map_count", "current_btd6_ver"
    ]
    for key in body["config"]:
        if key not in allowed_keys:
            return {"": f"Found wrong key \"{key}\""}

    errors = {}
    config = await get_config()
    for key in body["config"]:
        idx = index_where(config, lambda x: x.name == key)
        vtype = type(config[idx].value)
        try:
            body["config"][key] = vtype(body["config"][key])
        except ValueError:
            errors[key] = f"Must be of type {vtype.__name__}"
    return errors


@src.utils.routedecos.bearer_auth
@src.utils.routedecos.validate_json_body(put_validate)
@src.utils.routedecos.with_maplist_profile
async def put(_r: web.Request, json_body: dict = None, maplist_profile: dict = None, **_kwargs):
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
            type: array
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
    if MAPLIST_LISTMOD_ID not in maplist_profile["roles"]:
        return web.json_response({"errors": {"": "You are not a Maplist Moderator"}, "data": {}}, status=401)

    await update_config(json_body["config"])
    return web.json_response({"errors": {}, "data": json_body["config"]})
