import asyncio
from aiohttp import web
from src.utils.misc import index_where
from src.db.queries.misc import get_config, update_config
import src.utils.routedecos
import src.log


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
    config = await get_config()
    return web.json_response({
        key: config[key].to_dict() for key in config
    })


async def put_validate(body: dict) -> dict:
    if "config" not in body:
        return {"config": "Missing"}
    if not isinstance(body["config"], dict):
        return {"config": "Must be of type object"}

    errors = {}
    config = await get_config()

    for key in body["config"]:
        if key not in config:
            return {key: "Invalid key"}

    for key in body["config"]:
        vtype = type(config[key].value)
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
        permissions: "src.db.models.Permissions" = None,
        **_kwargs
):
    """
    ---
    description: |
      Change any number of config variables. Must have edit:config on the variables you're editing.
      Changes to variables you don't have access to will be ignored.
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
        description: Your token is missing, invalid, or you don't have the privileges for this.
    """

    changed_vars = await update_config(json_body["config"], permissions.formats_where("edit:config"))
    asyncio.create_task(src.log.log_action("config", "put", None, json_body["config"], discord_profile["id"]))
    return web.json_response({"errors": {}, "data": changed_vars})
