from aiohttp import web


async def get(request: web.Request):
    return web.Response(status=200, text="Here's all exmaps/{code}")


async def post(request: web.Request):
    return web.Response(status=200, text="Posted a exmap/{code}")


async def put(request: web.Request):
    return web.Response(status=200, text="Put a exmap/{code}")


async def delete(request: web.Request):
    return web.Response(status=200, text="Deleted a exmap/{code}")
