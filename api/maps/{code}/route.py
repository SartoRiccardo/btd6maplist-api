import asyncio
from aiohttp import web
import http
import src.log
from src.db.queries.maps import get_map, edit_map, delete_map
from src.utils.forms import get_map_form
from src.utils.formats.formatinfo import format_info
from src.utils.embeds import map_change_update_map_submission_wh
import src.utils.routedecos
from src.exceptions import MissingPermsException


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
@src.utils.routedecos.with_discord_profile
@src.utils.routedecos.require_perms()
async def put(
        request: web.Request,
        resource: "src.db.models.PartialMap" = None,
        discord_profile: dict = None,
        permissions: "src.db.models.Permissions" = None,
        **_kwargs,
) -> web.Response:
    """
    ---
    description: Edit a map. Must have edit:map perms.
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
        description: Your token is missing, invalid, or you don't have the privileges for this.
      "404":
        description: No map with that ID was found.
    """
    if not permissions.has_in_any("edit:map"):
        raise MissingPermsException("edit:map")

    json_body = await get_map_form(request, check_dup_code=False, editing=True)
    if isinstance(json_body, web.Response):
        return json_body

    json_body["code"] = resource.code
    for format_id in format_info:
        if not permissions.has("edit:map", format_id) and format_info[format_id].key in json_body:
            del json_body[format_info[format_id].key]

    await edit_map(json_body, resource)
    asyncio.create_task(map_change_update_map_submission_wh(resource.code, json_body))
    asyncio.create_task(src.log.log_action("map", "put", resource.code, json_body, discord_profile["id"]))
    return web.Response(status=http.HTTPStatus.NO_CONTENT)


@src.utils.routedecos.bearer_auth
@src.utils.routedecos.validate_resource_exists(get_map, "code", partial=True)
@src.utils.routedecos.with_discord_profile
@src.utils.routedecos.require_perms()
async def delete(
        _r: web.Request,
        discord_profile: dict = None,
        resource: "src.db.models.PartialMap" = None,
        permissions: "src.db.models.Permissions" = None,
        **_kwargs
):
    """
    ---
    description: |
      Soft deletes a map. Must have delete:map.
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
        description: Your token is missing, invalid, or you don't have the privileges for this.
      "404":
        description: No map with that ID was found.
    """
    if not permissions.has_in_any("delete:map"):
        raise MissingPermsException("delete:map")

    if resource.deleted_on:
        return web.Response(status=http.HTTPStatus.NO_CONTENT)

    fields_values = []
    for format_id in format_info:
        if permissions.has("delete:map", format_id):
            fields_values.append(format_info[format_id].key)

    await delete_map(resource.code, map_current=resource, keys=fields_values)
    asyncio.create_task(src.log.log_action("map", "delete", resource.code, None, discord_profile["id"]))
    return web.Response(status=http.HTTPStatus.NO_CONTENT)
