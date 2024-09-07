from aiohttp import web
from src.db.queries.completions import get_completion
import http
import src.utils.routedecos


@src.utils.routedecos.bearer_auth
@src.utils.routedecos.validate_resource_exists(get_completion, "cid")
@src.utils.routedecos.with_maplist_profile
async def post(
        _r: web.Request,
        maplist_profile: dict = None,
        resouce: "src.db.models.ListCompletion" = None
) -> web.Response:
    return web.Response(status=http.HTTPStatus.NOT_IMPLEMENTED)
