import http
from aiohttp import web
import src.utils.routedecos
from src.db.queries.achievement_roles import get_roles, update_ach_roles
from src.utils.validators import validate_achievement_roles
from src.utils.formats import is_format_expert, is_format_maplist


@src.utils.routedecos.bearer_auth
@src.utils.routedecos.with_discord_profile
@src.utils.routedecos.require_perms()
@src.utils.routedecos.validate_json_body(validate_achievement_roles)
async def put(
        _r: web.Request,
        permissions: "src.db.models.Permissions" = None,
        json_body: dict = None,
        **_kwargs,
) -> web.Response:
    """
    ---
    description: Modify Achivement Roles for a specific leaderboard. Must have edit:achievement_roles.
    tags:
    - Roles
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              lb_format:
                $ref: "#/components/schemas/MaplistFormat"
              lb_type:
                type: string
                enum: [points, no_geraldo, black_border, lccs]
                description: The subtype of the leaderboard.
              roles:
                type: array
                items:
                  $ref: "#/components/schemas/AchievementRole"
    responses:
      "204":
        description: The roles were modified correctly
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
        description: No completion with that ID was found.
    """
    if not permissions.has("edit:achievement_roles", json_body["lb_format"]):
        return web.json_response(
            {"errors": {"lb_format": f"You are missing `edit:achievement_roles` on {json_body['lb_format']}"}},
            status=http.HTTPStatus.FORBIDDEN,
        )

    await update_ach_roles(json_body["lb_format"], json_body["lb_type"], json_body["roles"])
    return web.Response(status=http.HTTPStatus.NO_CONTENT)


async def get(_r: web.Request) -> web.Response:
    """
    ---
    description: Returns all available Achievement Roles.
    tags:
    - Roles
    responses:
      "200":
        description: Returns an array of `AchievementRole`.
        content:
          application/json:
            schema:
              type: array
              items:
                $ref: "#/components/schemas/AchievementRole"
    """
    return web.json_response([rl.to_dict() for rl in await get_roles()])
