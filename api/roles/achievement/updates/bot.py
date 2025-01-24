from aiohttp import web
import src.utils.routedecos


@src.utils.routedecos.check_bot_signature(no_content=True)
async def get(request: web.Request) -> web.Response:
    pass


@src.utils.routedecos.check_bot_signature(no_content=True)
async def post(request: web.Request) -> web.Response:
    pass
