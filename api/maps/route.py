from aiohttp import web


async def get(request: web.Request):
    return web.Response(status=200, text="Here's all maps")


async def post(request: web.Request):
    return web.Response(status=200, text="Posted a map")


async def put(request: web.Request):
    return web.Response(status=200, text="Put a map")


async def delete(request: web.Request):
    return web.Response(status=200, text="Deleted a map")
