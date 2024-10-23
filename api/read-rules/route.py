from aiohttp import web
import http
import src.utils.routedecos
from src.db.queries.users import read_rules


@src.utils.routedecos.bearer_auth
@src.utils.routedecos.with_discord_profile
async def put(
        _r: web.Request,
        discord_profile: dict = None,
        **_kwargs
) -> web.Response:
    await read_rules(int(discord_profile["id"]))
    return web.Response(status=http.HTTPStatus.NO_CONTENT)
