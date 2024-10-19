from aiohttp import web
from src.db.queries.maps import get_expert_maps


async def get(_r: web.Request):
    """
    ---
    description: Returns a list of maps in the Expert List.
    tags:
    - Map Lists
    responses:
      "200":
        description: Returns an array of `PartialExpertMap`.
        content:
          application/json:
            schema:
              type: array
              items:
                $ref: "#/components/schemas/PartialExpertMap"
    """
    maps = await get_expert_maps()
    return web.json_response([m.to_dict() for m in maps])
