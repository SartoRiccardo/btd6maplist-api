import http
from aiohttp import web
from src.db.queries.users import create_user
from src.utils.validators import validate_discord_user
import src.utils.routedecos


@src.utils.routedecos.bearer_auth
@src.utils.routedecos.validate_json_body(validate_discord_user)
@src.utils.routedecos.with_maplist_profile
@src.utils.routedecos.require_perms()
async def post(
        _r: web.Request,
        json_body: dict = None,
        **_kwargs,
) -> web.Response:
    """
    ---
    description: Manually inserts a new user. Must be a moderator.
    tags:
    - Users
    requestBody:
      required: true
      content:
        application/json:
          schema:
            $ref: "#/components/schemas/PartialUser"
    responses:
      "201":
        description: The user was created successfully
      "400":
        description: Returns the errors with the request.
        content:
          application/json:
            schema:
              type: object
              properties:
                errors:
                  type: object
                  description: |
                    Object where the key is the name of the wrong field and
                    the value is the description.
    """
    success = await create_user(json_body["discord_id"], json_body["name"])
    if success:
        return web.Response(status=http.HTTPStatus.CREATED)

    return web.json_response(
        {"errors": {
            "discord_id": "One or both of these already exists",
            "name": "One or both of these already exists",
        }},
        status=http.HTTPStatus.BAD_REQUEST,
    )
