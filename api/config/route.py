from aiohttp import web
from src.db.queries.misc import get_config


async def get(request: web.Request):
    return web.json_response([cfg.to_dict() for cfg in await get_config()])
