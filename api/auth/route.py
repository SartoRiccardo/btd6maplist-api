from aiohttp import web
from src.db.queries.users import create_user, get_user
import src.http


async def post(request: web.Request):
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
        "maplist_profile": (await get_user(disc_profile["id"])).to_dict(with_oak=True)
    })
