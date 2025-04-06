from aiohttp import web
from src.db.queries.maps import get_retro_maps


async def get(_r: web.Request) -> web.Response:
    """
    ---
    description: Returns a list of retro maps.
    tags:
    - Map Lists
    responses:
      "200":
        description: |
          An object where each key is a game name, each value is another object
          where each key is a category name, where each value is a list of
          NamedResource.
        content:
          application/json:
            schema:
              type: object
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
