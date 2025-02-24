import http
from aiohttp import web
import src.utils.routedecos
from src.db.queries.achievement_roles import refresh_lb_linked_role_snapshot, get_lb_linked_role_updates


@src.utils.routedecos.check_bot_signature(no_content=True)
async def get(_r: web.Request) -> web.Response:
    updates = await get_lb_linked_role_updates()
    return web.json_response([u.to_dict() for u in updates])


@src.utils.routedecos.check_bot_signature(no_content=True)
async def post(_r: web.Request) -> web.Response:
    await refresh_lb_linked_role_snapshot()
    return web.Response(status=http.HTTPStatus.NO_CONTENT)
