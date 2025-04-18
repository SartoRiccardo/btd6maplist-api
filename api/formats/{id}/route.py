import http
import src.utils.routedecos
from aiohttp import web
from src.db.queries.format import get_format, edit_format
from src.utils.validators import validate_format
from src.exceptions import GenericErrorException, MissingPermsException


@src.utils.routedecos.bearer_auth
@src.utils.routedecos.validate_resource_exists(get_format, "id")
@src.utils.routedecos.with_discord_profile
@src.utils.routedecos.require_perms()
async def get(
        _r: web.Request,
        resource: "src.db.models.Format" = None,
        permissions: "src.db.models.Permissions" = None,
        **_kwargs,
) -> web.Response:
    """
    ---
    description: |
      Get in-depth information about a format. Must have edit:config perms.
      It's gated as it has sensitive info (webhook urls)
    tags:
    - Map Lists
    parameters:
    - in: path
      name: id
      required: true
      schema:
        type: integer
      description: The format's ID.
    requestBody:
      required: true
      content:
        application/json:
          schema:
            $ref: "#/components/schemas/Format"
    responses:
      "200":
        description: The full format info.
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/FullFormat"
      "401":
        description: Your token is missing, invalid, or you don't have the privileges for this.
      "403:
        description: You don't have the necessary permissions to do this.
      "404":
        description: No format with that ID was found.
    """
    if not permissions.has("edit:config", resource.id):
        raise MissingPermsException("edit:config", resource.id)

    return web.json_response(resource.to_full_dict())


@src.utils.routedecos.bearer_auth
@src.utils.routedecos.validate_resource_exists(get_format, "id")
@src.utils.routedecos.with_discord_profile
@src.utils.routedecos.require_perms()
async def put(
        request: web.Request,
        resource: "src.db.models.Format" = None,
        permissions: "src.db.models.Permissions" = None,
        **_kwargs,
) -> web.Response:
    """
    ---
    description: Edit a format. Must have edit:config perms.
    tags:
    - Map Lists
    parameters:
    - in: path
      name: id
      required: true
      schema:
        type: integer
      description: The format's ID.
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              hidden:
                type: boolean
                description: Whether maps with this format should be hidden.
              run_submission_status:
                type: int
                description: Whether submissions are open, closed, ...
                enum: ["open", "closed", "lcc_only"]
              map_submission_status:
                type: int
                description: Whether map submissions are open, closed, ...
                enum: ["open", "closed"]
              run_submission_wh:
                type: string
                nullable: true
                description: The webhook URL to send Discord embed-like information about completion submissions.
              map_submission_wh:
                type: string
                nullable: true
                description: The webhook URL to send Discord embed-like information about map submissions.
    responses:
      "204":
        description: The resource was modified correctly
      "400":
        description: |
          One of the fields is badly formatted.
        content:
          application/json:
            schema:
              type: object
              properties:
                errors:
                  type: object
                  description: Each key-value pair is the key of the wrong field and a description as to why.
      "401":
        description: Your token is missing, invalid, or you don't have the privileges for this.
      "403:
        description: You don't have the necessary permissions to do this.
      "404":
        description: No format with that ID was found.
    """
    if not permissions.has("edit:config", resource.id):
        return web.Response(status=http.HTTPStatus.FORBIDDEN)

    if request.content_type == "application/json":
        json_data = await request.json()
    else:
        raise GenericErrorException("Unsupported Content-Type")

    await validate_format(json_data)

    await edit_format(
        resource.id,
        json_data["hidden"],
        json_data["run_submission_status"],
        json_data["map_submission_status"],
        json_data["map_submission_wh"],
        json_data["run_submission_wh"],
    )

    return web.Response(status=http.HTTPStatus.NO_CONTENT)
