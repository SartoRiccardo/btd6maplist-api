from aiohttp import web
from src.db.queries.users import create_user, get_user
import src.http


async def post(request: web.Request):
    """
    ---
    description: |
      Creates an user based on a Discord profile if it's not in the database, and
      returns its discord profile alongside its Maplist profile.
    tags:
    - Users
    parameters:
    - in: query
      name: discord_token
      required: true
      schema:
        type: string
      description: The user's Discord OAuth2 Access Token.
    responses:
      "200":
        description: Returns the user's Discord profile and its maplist profile.
        content:
          application/json:
            schema:
              type: object
              properties:
                discord_profile:
                  type: object
                  description: Check out Discord's documentation for this field's schema.
                maplist_profile:
                  $ref: "#/components/schemas/Profile"
      "400":
        description: "`discord_token` is missing or invalid."
    """
    if "discord_token" not in request.query:
        return web.json_response(
            {
                "error": 'Missing discord_token',
            },
            status=400,
        )

    token = request.query["discord_token"]
    disc_response = await src.http.http.get(
        "https://discord.com/api/v10/users/@me",
        headers={"Authorization": f"Bearer {token}"}
    )
    if disc_response.status != 200:
        return web.json_response(
            {
                "error": 'Invalid discord_token',
            },
            status=400,
        )

    disc_profile = await disc_response.json()
    await create_user(disc_profile["id"], disc_profile["username"])

    return web.json_response({
        "discord_profile": disc_profile,
        "maplist_profile": (
            await get_user(
                disc_profile["id"],
                with_completions=True)
        ).to_dict(profile=True, with_completions=True)
    })
