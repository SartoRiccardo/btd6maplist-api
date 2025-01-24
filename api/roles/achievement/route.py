from aiohttp import web
import src.utils.routedecos
from src.db.queries.achievement_roles import get_roles


@src.utils.routedecos.bearer_auth
@src.utils.routedecos.with_discord_profile
@src.utils.routedecos.require_perms()
async def put(request: web.Request) -> web.Response:
    pass


async def get(request: web.Request) -> web.Response:
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
    return web.json_response(await get_roles())
