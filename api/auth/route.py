from aiohttp import web
from src.db.queries.users import get_user
import src.utils.routedecos


@src.utils.routedecos.bearer_auth
@src.utils.routedecos.with_discord_profile
@src.utils.routedecos.register_user
async def post(
        _r: web.Request,
        discord_profile: dict = None,
        **_kwargs,
):
    """
    ---
    description: |
      Creates a user based on a Discord profile if it's not in the database, and
      returns its Maplist profile.
    tags:
    - Authentication
    responses:
      "200":
        description: Returns the user's Maplist profile.
        content:
          application/json:
            schema:
              type: object
              properties:
                maplist_profile:
                  $ref: "#/components/schemas/FullProfile"
      "401":
        description: "`discord_token` is missing or invalid."
    """
    user_profile = await get_user(discord_profile["id"], with_completions=True)
    return web.json_response(user_profile.to_dict(profile=True, with_completions=True))
