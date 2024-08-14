from aiohttp import web
from src.db.queries.leaderboard import get_maplist_leaderboard


async def get(request: web.Request):
    current_version = True
    if "version" in request.query:
        version = request.query["version"].lower()
        if version.lower() == "all":
            current_version = False
        elif version != "current":
            return web.json_response(
                {
                    "error": 'Allowed values for "ver": ["current", "all"]'
                },
                status=400,
            )

    lb = await get_maplist_leaderboard(curver=current_version)
    return web.json_response([entry.to_dict() for entry in lb])
