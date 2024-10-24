from aiohttp import web
from src.db.queries.maps import get_legacy_maps


async def get(_r: web.Request) -> web.Response:
    """
    ---
    description: Returns a list of deleted/pushed off maps.
    tags:
    - Map Lists
    responses:
      "200":
        description: Returns an array of `PartialListMap`.
        content:
          application/json:
            schema:
              type: array
              items:
                $ref: "#/components/schemas/PartialListMap"
    """
    maps = await get_legacy_maps()
    return web.json_response([m.to_dict() for m in maps])
