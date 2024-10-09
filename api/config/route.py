import asyncio
from aiohttp import web
from src.utils.misc import index_where
from src.db.queries.misc import get_config, update_config
import src.utils.routedecos
import src.log

var_perms = {
    "points_top_map": (True, False),
    "points_bottom_map": (True, False),
    "formula_slope": (True, False),
    "points_extra_lcc": (True, False),
    "points_multi_gerry": (True, False),
    "points_multi_bb": (True, False),
    "decimal_digits": (True, False),
    "map_count": (True, False),
    "current_btd6_ver": (True, True),
    "exp_points_casual": (False, True),
    "exp_points_medium": (False, True),
    "exp_points_high": (False, True),
    "exp_points_true": (False, True),
    "exp_points_extreme": (False, True),
}


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

    for key in body["config"]:
        if key not in var_perms:
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
@src.utils.routedecos.require_perms()
async def put(
        _r: web.Request,
        json_body: dict = None,
        maplist_profile: dict = None,
        is_admin: bool = False,
        is_maplist_mod: bool = False,
        is_explist_mod: bool = False,
        **_kwargs
):
    """
    ---
    description: |
      Change any number of the config variables. Certain roles have access to change different variables.
      Must be a Maplist or Expert List Moderator. Changes to variables you don't have access to will be ignored.
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
    if not is_admin:
        cvar_keys = list(json_body["config"].keys())
        for key in cvar_keys:
            check_ml_mod, check_exp_mod = var_perms[key]
            if not (check_ml_mod and is_maplist_mod) and \
                    not (check_exp_mod and is_explist_mod):
                del json_body["config"][key]

    await update_config(json_body["config"])
    asyncio.create_task(src.log.log_action("config", "put", None, json_body["config"], maplist_profile["user"]["id"]))
    return web.json_response({"errors": {}, "data": json_body["config"]})
