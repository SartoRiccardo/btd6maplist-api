import asyncio
import http
from aiohttp import web
import src.utils.routedecos
import src.log
from src.db.queries.maps import get_map
from src.db.queries.completions import transfer_all_completions


async def validate_map_is_valid(json_body: dict) -> dict:
    if "code" not in json_body:
        return {"code": "Missing field"}
    if not isinstance(json_body["code"], str):
        return {"code": "Must be a string"}

    errors = {}
    new_map = await get_map(json_body["code"])
    if new_map is None:
        return {"": "That map is not in the maplist!"}
    if new_map.deleted_on is not None:
        return {"": "That map is deleted too!"}
    json_body["code"] = new_map.code

    return errors


@src.utils.routedecos.bearer_auth
@src.utils.routedecos.validate_resource_exists(get_map, "code", partial=True)
@src.utils.routedecos.validate_json_body(validate_map_is_valid)
@src.utils.routedecos.with_maplist_profile
@src.utils.routedecos.require_perms()
async def put(
        _r: web.Request,
        resource: "src.db.models.PartialMap" = None,
        maplist_profile: dict = None,
        is_explist_mod: bool = False,
        is_list_mod: bool = False,
        json_body: dict = None,
        **_kwargs,
) -> web.Response:
    """
    ---
    description: |
      Transfer all completions of this map to another. Only works if the current map is deleted.
      Must be a Maplist or Expert List Moderator.
    tags:
    - Completions
    parameters:
    - in: path
      name: code
      required: true
      schema:
        type: string
      description: The map's code.
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              code:
                type: string
                description: The code of the new map you want to transfer the completions to.
    responses:
      "204":
        description: The completions were transferred over correctly
      "400":
        description: The map you're trying to transfer completions from was not deleted.
      "401":
        description: Your token is missing or invalid.
      "403":
        description: You don't have the privileges for this.
      "404":
        description: No map with that ID was found.
    """
    if resource.deleted_on is None:
        return web.json_response(
            {"errors": {"": "You can only transfer completions from a deleted map"}},
            status=http.HTTPStatus.BAD_REQUEST,
        )

    await transfer_all_completions(
        resource.code,
        json_body["code"],
        transfer_list_comps=is_list_mod,
        transfer_explist_comps=is_explist_mod,
    )
    asyncio.create_task(
        src.log.log_action("completion", "put", resource.code, json_body["code"], maplist_profile["user"]["id"])
    )
    return web.Response(status=http.HTTPStatus.NO_CONTENT)
