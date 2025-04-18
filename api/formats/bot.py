from aiohttp import web
from src.db.queries.format import get_formats
import src.utils.routedecos


@src.utils.routedecos.check_bot_signature(no_content=True)
async def get(
        _r: web.Request,
) -> web.Response:
    return web.json_response(
        [fmt.to_full_dict() for fmt in await get_formats()]
    )
