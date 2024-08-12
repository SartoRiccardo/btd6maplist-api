from aiohttp import web
from src.db.queries.maps import get_expert_maps


async def get(_r: web.Request):
    maps = await get_expert_maps()
    return web.json_response([m.to_dict() for m in maps])
