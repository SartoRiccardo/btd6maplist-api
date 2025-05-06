import http
from aiohttp import web
from src.db.queries.users import get_user
from src.requests import ninja_kiwi_api


async def get(
        request: web.Request,
) -> web.Response:
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
    - in: query
      name: minimal
      required: false
      schema:
        type: boolean
      description: Only returns the name, id, and flair if `true`. Default is `false`.
    responses:
      "200":
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/User"
    """
    user_id = request.match_info.get("uid")
    minimal = request.query.get("minimal", "false").lower() == "true"
    if user_id is None or (user := await get_user(user_id, minimal=minimal)) is None:
        return web.Response(status=http.HTTPStatus.NOT_FOUND)

    deco = {"avatarURL": None, "bannerURL": None}
    if user.oak:
        deco = await ninja_kiwi_api().get_btd6_user_deco(user.oak)
    return web.json_response({
        **user.to_dict(),
        **deco,
    })
