from aiohttp import web
from src.db.queries.leaderboard import (
    get_maplist_leaderboard,
    get_maplist_lcc_leaderboard,
)


async def get(request: web.Request):
    current_version = True
    if "version" in request.query:
        version = request.query["version"].lower()
        if version.lower() == "all":
            current_version = False
        elif version != "current":
            return web.json_response(
                {
                    "error": 'Allowed values for "version": ["current", "all"]'
                },
                status=400,
            )

    value = "points"
    if "value" in request.query:
        value = request.query["value"].lower()
        if value not in ["points", "lccs"]:
            return web.json_response(
                {
                    "error": 'Allowed values for "value": ["points", "lccs"]'
                },
                status=400,
            )

    if value == "points":
        lb = await get_maplist_leaderboard(curver=current_version)
    else:
        lb = await get_maplist_lcc_leaderboard(curver=current_version)
    return web.json_response([entry.to_dict() for entry in lb])
