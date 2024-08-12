from aiohttp import web


async def get(request: web.Request):
    return web.Response(status=200, text="Here's all maps/leaderboard")


async def post(request: web.Request):
    return web.Response(status=200, text="Posted a map/leaderboard")


async def put(request: web.Request):
    return web.Response(status=200, text="Put a map/leaderboard")


async def delete(request: web.Request):
    return web.Response(status=200, text="Deleted a map/leaderboard")
