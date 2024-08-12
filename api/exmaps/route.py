from aiohttp import web
from src.db.queries.exmaps import list_maps


async def get(_r: web.Request):
    maps = await list_maps()
    return web.json_response([m.to_dict() for m in maps])
