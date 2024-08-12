from aiohttp import web
from src.db.queries.maps import list_maps


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

    maps = await list_maps(curver=current_version)
    return web.json_response([m.to_dict() for m in maps])
