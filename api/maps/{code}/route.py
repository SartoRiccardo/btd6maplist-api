from aiohttp import web
from src.db.queries.maps import get_map


async def get(request: web.Request):
    map_data = await get_map(request.match_info["code"])
    if map_data is None:
        return web.json_response({"error": "No map with that ID found."}, status=404)
    return web.json_response(map_data.to_dict())
