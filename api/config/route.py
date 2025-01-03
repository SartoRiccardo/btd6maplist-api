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
    "exp_nogerry_points_casual": (False, True),
    "exp_nogerry_points_medium": (False, True),
    "exp_nogerry_points_high": (False, True),
    "exp_nogerry_points_true": (False, True),
    "exp_nogerry_points_extreme": (False, True),
}


async def get(_r: web.Request):
    """
    ---
    description: Returns a list of config variables for the project.
    tags:
    - Config
    responses:
      "200":
        description: Returns the project's config variables.
        content:
          application/json:
            schema:
              type: object
    """
    return web.json_response(await get_config())


async def put_validate(body: dict) -> dict:
    if "config" not in body:
        return {"config": "Missing"}
    if not isinstance(body["config"], dict):
        return {"config": "Must be of type object"}

    for key in body["config"]:
        if key not in var_perms:
            return {key: "Invalid key"}

    errors = {}
    config = await get_config()
    for key in body["config"]:
        vtype = type(config[key])
        try:
            body["config"][key] = vtype(body["config"][key])
        except (ValueError, TypeError):
            errors[key] = f"Must be of type {vtype.__name__}"
    return errors


@src.utils.routedecos.bearer_auth
@src.utils.routedecos.with_discord_profile
@src.utils.routedecos.require_perms()
@src.utils.routedecos.validate_json_body(put_validate)
async def put(
        _r: web.Request,
        json_body: dict = None,
        discord_profile: dict = None,
        is_admin: bool = False,
        is_list_mod: bool = False,
        is_explist_mod: bool = False,
        **_kwargs
):
    """
    ---
    description: |
      Change any number of the config variables. Certain roles have access to change different variables.
      Must be a Maplist or Expert List Moderator. Changes to variables you don't have access to will be ignored.
    tags:
    - Config
    requestBody:
      required: true
      content:
        application/json:
          schema:
            description: The variables you want to change and the new values.
            type: object
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
                  type: object
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
            if not (check_ml_mod and is_list_mod or check_exp_mod and is_explist_mod):
                del json_body["config"][key]

    await update_config(json_body["config"])
    asyncio.create_task(src.log.log_action("config", "put", None, json_body["config"], discord_profile["id"]))
    return web.json_response({"errors": {}, "data": json_body["config"]})
