from aiohttp import web
from src.db.queries.users import get_user
from src.ninjakiwi import get_btd6_user_deco


async def get(request: web.Request):
    user_data = await get_user(request.match_info["uid"])
    if user_data is None:
        return web.json_response({"error": "No user with that ID found."}, status=404)
    deco = {"avatarURL": None, "bannerURL": None}
    if user_data.oak:
        deco = await get_btd6_user_deco(user_data.oak)
    return web.json_response({
        **user_data.to_dict(),
        **deco,
    })
