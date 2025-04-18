import asyncio
import src.utils.routedecos
import http
import src.http
import src.log
from aiohttp import web
from src.exceptions import ValidationException
from src.db.queries.maps import add_map
from src.utils.embeds import map_change_update_map_submission_wh
from src.utils.forms import get_map_form
from src.utils.formats.formatinfo import format_info
from src.exceptions import MissingPermsException


async def get(request: web.Request):
    """
    ---
    description: Returns a list of maps in any maplist.
    tags:
    - Map Lists
    parameters:
    - in: query
      name: format
      required: false
      schema:
        $ref: "#/components/schemas/MaplistFormat"
      description: The version of the list to get. Defaults to `1`.
    - in: query
      name: filter
      required: false
      schema:
        type: integer
      description: |
        A filter for maps in the format you're requesting. In some formats are required.
        It changes meaning depending on the format you're requesting.
        - In the Maplist, it has no effect.
        - In the Nostalgia Pack, it filters the game. It's required here.
        - In BoTB/Expert List, it filters the difficulty. It's required in BoTB.
    responses:
      "200":
        description: Returns an array of `MinimalMap`.
        content:
          application/json:
            schema:
              type: array
              items:
                $ref: "#/components/schemas/MinimalMap"
      "400":
        description: Invalid request.
    """
    format_id = request.query.get("format", "1")
    if not format_id.isnumeric():
        raise ValidationException({"format": "Must be numeric"})
    format_id = int(format_id)

    filter_value = request.query.get("filter", None)
    if filter_value is not None:
        if not filter_value.isnumeric():
            raise ValidationException({"filter": "Must be numeric"})
        else:
            filter_value = int(filter_value)

    maps = []
    if format_id in format_info:
        maps = await format_info[format_id].get_maps(filter_value)
    return web.json_response([m.to_dict() for m in maps])


@src.utils.routedecos.bearer_auth
@src.utils.routedecos.with_discord_profile
@src.utils.routedecos.require_perms()
async def post(
        request: web.Request,
        discord_profile: dict = None,
        permissions: "src.db.models.Permissions" = None,
        **_kwargs
) -> web.Response:
    """
    ---
    description: Add a map. Must have create:map.
    tags:
    - Maps
    requestBody:
      required: true
      content:
        multipart/form-data:
          schema:
            type: object
            required: [data]
            properties:
              data:
                $ref: "#/components/schemas/MapPayload"
              r6_start:
                type: string
                format: binary
              map_preview_url:
                type: string
                format: binary
    responses:
      "201":
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
        description: Your token is missing, invalid, or you don't have the privileges for this.
    """
    json_body = await get_map_form(request, check_dup_code=True)
    if isinstance(json_body, web.Response):
        return json_body

    missing_perms_on = []
    for format_id in format_info:
        if json_body.get(format_info[format_id].key, None) is not None \
                and not permissions.has("create:map", format_id):
            missing_perms_on.append(format_id)
    if len(missing_perms_on):
        raise MissingPermsException("create:map", missing_perms_on)

    await add_map(json_body)
    asyncio.create_task(map_change_update_map_submission_wh(json_body["code"], json_body))
    asyncio.create_task(src.log.log_action("map", "post", None, json_body, discord_profile["id"]))
    return web.Response(status=http.HTTPStatus.CREATED)
