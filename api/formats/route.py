from aiohttp import web
from src.db.queries.format import get_formats


async def get(
        _r: web.Request,
) -> web.Response:
    """
    ---
    description: Returns a list of formats.
    tags:
    - Map Lists
    responses:
      "200":
        description: Returns an array of `Format`.
        content:
          application/json:
            schema:
              type: array
              items:
                $ref: "#/components/schemas/Format"
    """
    return web.json_response(
        [fmt.to_dict() for fmt in await get_formats()]
    )
