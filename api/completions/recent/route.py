from aiohttp import web
from src.db.queries.completions import get_recent

AMOUNT = 5


async def get(request: web.Request) -> web.Response:
    """
    ---
    description: Gets the most recent completions.
    tags:
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
        description: Returns an array of completions.
        content:
          application/json:
            schema:
              type: array
              items:
                allOf:
                - $ref: "#/components/schemas/ListCompletionWithMeta"
                - type: object
                  properties:
                    map:
                      $ref: "#/components/schemas/PartialMap"
                    users:
                      type: array
                      items:
                        $ref: "#/components/schemas/DiscordID"
    """
    formats = [int(fmt) for fmt in request.query.get("formats", "1,51").split(",")]
    comps = await get_recent(limit=AMOUNT, formats=formats)
    return web.json_response([x.to_dict() for x in comps])
