from aiohttp import web
from src.db.queries.users import get_user
from src.requests import ninja_kiwi_api


async def get(request: web.Request):
    """
    ---
    description: Returns a user's data.
    tags:
    - Users
    parameters:
    - in: path
      name: uid
      required: true
      schema:
        type: integer
      description: The user's Discord ID.
    responses:
      "200":
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/User"
    """
    user_data = await get_user(request.match_info["uid"])
    if user_data is None:
        return web.json_response({"error": "No user with that ID found."}, status=404)
    deco = {"avatarURL": None, "bannerURL": None}
    if user_data.oak:
        deco = await ninja_kiwi_api().get_btd6_user_deco(user_data.oak)
    return web.json_response({
        **user_data.to_dict(),
        **deco,
    })
