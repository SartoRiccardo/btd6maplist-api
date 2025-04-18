from aiohttp import web
from src.db.queries.users import get_user
import src.utils.routedecos
from src.requests import ninja_kiwi_api


@src.utils.routedecos.validate_resource_exists(get_user, "uid")
async def get(
        _r: web.Request,
        resource: "src.db.models.User" = None,
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
    responses:
      "200":
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/User"
    """
    deco = {"avatarURL": None, "bannerURL": None}
    if resource.oak:
        deco = await ninja_kiwi_api().get_btd6_user_deco(resource.oak)
    return web.json_response({
        **resource.to_dict(),
        **deco,
    })
