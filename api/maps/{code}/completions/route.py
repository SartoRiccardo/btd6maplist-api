from aiohttp import web
from src.db.queries.maps import get_completions_for


ITEMS_PER_PAGE = 50


async def get(request: web.Request):
    """
    ---
    description: Returns a list of up to 50 maplist completions of this map.
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
    - in: query
      name: page
      required: false
      schema:
        type: integer
      description: Pagination. Defaults to `1`.
    responses:
      "200":
        description: Returns an array of `ListCompletion`.
        content:
          application/json:
            schema:
              type: array
              items:
                $ref: "#/components/schemas/ListCompletion"
    """
    completions, total = await get_completions_for(request.match_info["code"])
    return web.json_response({
        "total": total,
        "completions": [cmp.to_dict() for cmp in completions],
    })
