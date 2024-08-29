from aiohttp import web
from src.db.queries.maps import get_map, edit_map
import src.utils.routedecos
from src.utils.validators import validate_full_map
from config import MAPLIST_EXPMOD_ID, MAPLIST_LISTMOD_ID


@src.utils.routedecos.validate_resource_exists(get_map, "code")
async def get(_r: web.Request, resource: "src.db.models.Map" = None):
    """
    ---
    description: Returns an map's data.
    tags:
    - Expert List
    - The List
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
@src.utils.routedecos.validate_json_body(validate_full_map, check_dup_code=False)
@src.utils.routedecos.with_maplist_profile
async def put(
        _r: web.Request,
        json_body: dict = None,
        resource: "src.db.models.PartialMap" = None,
        maplist_profile: dict = None,
        **_kwargs
):
    """
    ---
    description: Edit a map. Must be a Maplist or Expert List Moderator.
    tags:
    - The List
    - Expert List
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
    if not (MAPLIST_EXPMOD_ID in maplist_profile["roles"] or MAPLIST_LISTMOD_ID in maplist_profile["roles"]):
        return web.json_response({"errors": {"": "You are not a moderator"}, "data": {}}, status=401)

    if MAPLIST_EXPMOD_ID not in maplist_profile["roles"]:
        del json_body["difficulty"]
    if MAPLIST_LISTMOD_ID not in maplist_profile["roles"]:
        del json_body["placement_allver"]
        del json_body["placement_curver"]

    await edit_map(json_body, resource)

    return web.Response(status=204)


@src.utils.routedecos.bearer_auth
@src.utils.routedecos.validate_resource_exists(get_map, "code", partial=True)
@src.utils.routedecos.with_maplist_profile
async def delete(
        _r: web.Request,
        maplist_profile: dict = None,
        resource: "src.db.models.PartialMap" = None,
        **_kwargs
):
    """
    ---
    description: |
      Soft deletes a map. Must be a Maplist or Expert List Moderator.
      Deleted maps and all their data are kept in the database, but ignored.
    tags:
    - The List
    - Expert List
    responses:
      "204":
        description: The resource was deleted correctly
      "401":
        description: Your token is missing, invalid or you don't have the privileges for this.
      "404":
        description: No map with that ID was found.
    """
    return web.Response(status=501)
