import src.utils.routedecos
import http
import src.http
import src.log
from aiohttp import web
from src.db.queries.maps import get_list_maps, add_map
from config import MAPLIST_LISTMOD_ID, MAPLIST_EXPMOD_ID, MAPLIST_ADMIN_IDS
from src.utils.forms import get_map_form


async def get(request: web.Request):
    """
    ---
    description: Returns a list of maps in The List.
    tags:
    - The List
    parameters:
    - in: query
      name: version
      required: false
      schema:
        type: string
        enum: [current, all]
      description: The version of the list to get. Defaults to `current`.
    responses:
      "200":
        description: Returns an array of `PartialListMap`.
        content:
          application/json:
            schema:
              type: array
              items:
                $ref: "#/components/schemas/PartialListMap"
      "400":
        description: Invalid request, the error will be specified in the `error` key.
    """
    current_version = True
    if "version" in request.query:
        version = request.query["version"].lower()
        if version.lower() == "all":
            current_version = False
        elif version != "current":
            return web.json_response(
                {
                    "error": 'Allowed values for "ver": ["current", "all"]'
                },
                status=http.HTTPStatus.BAD_REQUEST,
            )

    maps = await get_list_maps(curver=current_version)
    return web.json_response([m.to_dict() for m in maps])


@src.utils.routedecos.bearer_auth
@src.utils.routedecos.with_maplist_profile
@src.utils.routedecos.require_perms()
async def post(
        request: web.Request,
        maplist_profile: dict = None,
        is_admin: bool = False,
        **_kwargs
) -> web.Response:
    """
    ---
    description: Add a map. Must be a Maplist or Expert List Moderator.
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
        description: The resource was created correctly
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
    """
    json_body = await get_map_form(request, check_dup_code=True)

    errors = {}
    if not is_admin:
        if json_body["difficulty"] != -1 and MAPLIST_EXPMOD_ID not in maplist_profile["roles"]:
            errors["difficulty"] = "You are not an Expert List moderator"
        if json_body["placement_allver"] != -1 and MAPLIST_LISTMOD_ID not in maplist_profile["roles"]:
            errors["placement_allver"] = "You are not a List moderator"
        if json_body["placement_curver"] != -1 and MAPLIST_LISTMOD_ID not in maplist_profile["roles"]:
            errors["placement_curver"] = "You are not a List moderator"
    if len(errors):
        return web.json_response(
            {"errors": errors, "data": {}},
            status=http.HTTPStatus.BAD_REQUEST
        )

    await add_map(json_body)
    await src.log.log_action("map", "post", None, json_body, maplist_profile["user"]["id"])
    return web.Response(status=http.HTTPStatus.NO_CONTENT)
