import asyncio
import src.utils.routedecos
import http
import src.http
import src.log
from aiohttp import web
from src.exceptions import ValidationException
from src.db.queries.maps import get_retro_maps
from src.utils.embeds import update_map_submission_wh
from src.utils.forms import get_map_form
from src.utils.formats import format_idxs
from src.exceptions import MissingPermsException


async def get(request: web.Request):
    """
    ---
    description: Returns a list of retro maps.
    tags:
    - Map Lists
    responses:
      "200":
        description: Returns an array of `MinimalMap`.
        content:
          application/json:
            schema:
              type: array
              items:
                $ref: "#/components/schemas/MinimalMap"
      "400":
        description: Invalid request.
    """
    maps = await get_retro_maps()
    maps_return = {}
    for m in maps:
        if m.game_name not in maps_return:
            maps_return[m.game_name] = {}
        if m.category_name not in maps_return[m.game_name]:
            maps_return[m.game_name][m.category_name] = []
        maps_return[m.game_name][m.category_name].append({"id": m.id, "name": m.name})
    return web.json_response(maps_return)
