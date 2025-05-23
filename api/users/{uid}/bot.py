from aiohttp import web
import http
import src.utils.routedecos
from src.db.queries.users import get_user, edit_user, get_user_min, get_user_perms
from src.requests import ninja_kiwi_api


@src.utils.routedecos.check_bot_signature(path_params=["uid"], qparams=["no_load_oak"], no_content=True)
@src.utils.routedecos.validate_resource_exists(get_user, "uid")
async def get(
        request: web.Request,
        resource: "src.db.models.User" = None,
        **_kwargs,
) -> web.Response:
    """
    Identical to its non-bot counterpart but can omit BTD6 profile data, in
    case it needs to be faster for the 3-second interaction limit.
    """
    deco = {"avatarURL": None, "bannerURL": None}
    if resource.oak and not (request.query.get("no_load_oak", "false").lower() == "true"):
        deco = await ninja_kiwi_api().get_btd6_user_deco(resource.oak)
    return web.json_response({
        **resource.to_dict(profile=True),
        **deco,
        "permissions": (await get_user_perms(resource.id)).to_dict(),
    })


@src.utils.routedecos.check_bot_signature(path_params=["uid"])
@src.utils.routedecos.register_user
@src.utils.routedecos.validate_resource_exists(get_user_min, "uid")
async def put(
        request: web.Request,
        json_data: dict = None,
        resource: "src.db.models.PartialUser" = None,
        **_kwargs
) -> web.Response:
    """
    This bot route only modifies the user's OAK.
    There are no server-side checks on the validity of the OAK.
    """
    if json_data["user"]["id"] != request.match_info["uid"]:
        return web.Response(status=http.HTTPStatus.UNAUTHORIZED)

    oak = json_data["oak"] if len(json_data["oak"]) else None
    await edit_user(
        request.match_info["uid"],
        resource.name,
        oak,
    )
    return web.Response(status=http.HTTPStatus.OK)
