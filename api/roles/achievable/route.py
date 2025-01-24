from aiohttp import web
import src.utils.routedecos


@src.utils.routedecos.bearer_auth
@src.utils.routedecos.with_discord_profile
@src.utils.routedecos.require_perms()
async def put(request: web.Request) -> web.Response:
    pass
