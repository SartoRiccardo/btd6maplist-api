from aiohttp import web
import src.utils.routedecos
from src.db.queries.users import get_user
from src.ninjakiwi import get_btd6_user_deco


@src.utils.routedecos.check_bot_signature(path_params=["uid"])
@src.utils.routedecos.validate_resource_exists(get_user, "uid")
async def get(
        _r: web.Request,
        resource: "src.db.models.User" = None,
        **_kwargs,
) -> web.Response:
    deco = {"avatarURL": None, "bannerURL": None}
    if resource.oak:
        deco = await get_btd6_user_deco(resource.oak)
    return web.json_response({
        **resource.to_dict(profile=True),
        **deco,
    })
