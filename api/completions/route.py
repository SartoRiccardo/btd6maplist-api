from aiohttp import web
import http
import src.utils.routedecos


@src.utils.routedecos.bearer_auth
@src.utils.routedecos.with_maplist_profile
async def post(_r: web.Request, maplist_profile: dict = None) -> web.Response:
    return web.Response(status=http.HTTPStatus.NOT_IMPLEMENTED)
