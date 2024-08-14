from aiohttp import web
from src.db.queries.maps import get_completions_for


async def get(request: web.Request):
    completions = await get_completions_for(request.match_info["code"])
    return web.json_response([cmp.to_dict() for cmp in completions])
