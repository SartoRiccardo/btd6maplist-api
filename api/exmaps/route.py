from aiohttp import web


async def get(request: web.Request):
    return web.Response(status=200, text="Here's all exmaps")


async def post(request: web.Request):
    return web.Response(status=200, text="Posted a exmap")


async def put(request: web.Request):
    return web.Response(status=200, text="Put a exmap")


async def delete(request: web.Request):
    return web.Response(status=200, text="Deleted a exmap")
