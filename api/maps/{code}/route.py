import asyncio
from aiohttp import web
import http
import src.log
from src.db.queries.maps import get_map, edit_map, delete_map
from src.utils.forms import get_map_form
import src.utils.routedecos
from config import MAPLIST_EXPMOD_ID, MAPLIST_LISTMOD_ID


@src.utils.routedecos.validate_resource_exists(get_map, "code")
async def get(_r: web.Request, resource: "src.db.models.Map" = None):
    """
    ---
    description: Returns an map's data.
    tags:
    - Maps
    parameters:
    - in: path
      name: code
      required: true
      schema:
        type: string
      description: The map's code.
    responses:
      "200":
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/Map"
      "404":
        description: No map with that ID was found.
    """
    return web.json_response(resource.to_dict())


@src.utils.routedecos.bearer_auth
@src.utils.routedecos.validate_resource_exists(get_map, "code", partial=True)
@src.utils.routedecos.with_maplist_profile
@src.utils.routedecos.require_perms()
async def put(
        request: web.Request,
        resource: "src.db.models.PartialMap" = None,
        maplist_profile: dict = None,
        is_maplist_mod: bool = False,
        is_explist_mod: bool = False,
        **_kwargs,
):
    """
    ---
    description: Edit a map. Must be a Maplist or Expert List Moderator.
    tags:
    - Maps
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
            $ref: "#/components/schemas/Map"
    responses:
      "204":
        description: The resource was modified correctly
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
                  type: object
                  example: {}
      "401":
        description: Your token is missing, invalid or you don't have the privileges for this.
      "404":
        description: No map with that ID was found.
    """
    json_body = await get_map_form(request, check_dup_code=False, editing=True)
    if isinstance(json_body, web.Response):
        return json_body

    json_body["code"] = resource.code
    if not is_explist_mod:
        if "difficulty" in json_body:
            del json_body["difficulty"]
    if not is_maplist_mod:
        if "placement_allver" in json_body:
            del json_body["placement_allver"]
        if "placement_curver" in json_body:
            del json_body["placement_curver"]

    await edit_map(json_body, resource)
    asyncio.create_task(src.log.log_action("map", "put", resource.code, json_body, maplist_profile["user"]["id"]))
    return web.Response(status=http.HTTPStatus.NO_CONTENT)


@src.utils.routedecos.bearer_auth
@src.utils.routedecos.validate_resource_exists(get_map, "code", partial=True)
@src.utils.routedecos.with_maplist_profile
@src.utils.routedecos.require_perms()
async def delete(
        _r: web.Request,
        maplist_profile: dict = None,
        resource: "src.db.models.PartialMap" = None,
        is_admin: bool = False,
        **_kwargs
):
    """
    ---
    description: |
      Soft deletes a map. Must be a Maplist or Expert List Moderator.
      Deleted maps and all their data are kept in the database, but ignored.
    tags:
    - Maps
    parameters:
    - in: path
      name: code
      required: true
      schema:
        type: string
      description: The map's code.
    responses:
      "204":
        description: The resource was deleted correctly
      "401":
        description: Your token is missing, invalid or you don't have the privileges for this.
      "404":
        description: No map with that ID was found.
    """
    if resource.deleted_on:
        return web.Response(status=http.HTTPStatus.NO_CONTENT)

    modify_diff = is_admin or MAPLIST_EXPMOD_ID in maplist_profile["roles"]
    modify_pos = is_admin or MAPLIST_LISTMOD_ID in maplist_profile["roles"]

    if not resource.deleted_on:
        await delete_map(resource.code, map_current=resource, modify_diff=modify_diff, modify_pos=modify_pos)
        asyncio.create_task(src.log.log_action("map", "delete", resource.code, None, maplist_profile["user"]["id"]))

    return web.Response(status=http.HTTPStatus.NO_CONTENT)
