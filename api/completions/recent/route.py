from aiohttp import web
from src.db.queries.completions import get_recent

AMOUNT = 5


async def get(request: web.Request) -> web.Response:
    """
    ---
    description: Gets the most recent completions.
    tags:
    - Expert List
    - The List
    - Completions
    parameters:
    - in: query
      name: formats
      required: false
      schema:
        type: string
      description: The formats of the completions to get, comma separated.
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
    formats = [int(fmt) for fmt in request.query.get("formats", "1,51").split(",")]
    comps = await get_recent(limit=AMOUNT, formats=formats)
    return web.json_response([x.to_dict() for x in comps])
