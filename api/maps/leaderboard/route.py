from aiohttp import web
from src.db.queries.leaderboard import get_maplist_leaderboard


async def get(request: web.Request):
    lb = await get_maplist_leaderboard()
    return web.json_response([entry.to_dict() for entry in lb])
