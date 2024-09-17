from aiohttp import web
import http
import src.utils.routedecos
from src.db.queries.users import read_rules


@src.utils.routedecos.check_bot_signature()
@src.utils.routedecos.register_user
async def put(
        _r: web.Request,
        json_data: dict = None,
        **_kwargs
) -> web.Response:
    await read_rules(int(json_data["user"]["id"]))
    return web.Response(status=http.HTTPStatus.OK)
