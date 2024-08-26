from aiohttp import web
from src.db.queries.maps import get_map


async def get(request: web.Request):
    """
    ---
    description: Returns an map's data.
    tags:
    - Expert List
    - The List
    parameters:
    - in: path
      name: code
      required: true
      schema:
        type: string
      description: The map's code.
    responses:
      "200":
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/Map"
      "404":
        description: No map with that ID was found.
    """
    map_data = await get_map(request.match_info["code"])
    if map_data is None:
        return web.json_response({"error": "No map with that ID found."}, status=404)
    return web.json_response(map_data.to_dict())
