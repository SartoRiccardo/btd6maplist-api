from aiohttp import web
from src.db.queries.users import get_completions_by


PAGE_ENTRIES = 50


async def get(request: web.Request):
    """
    ---
    description: Returns a list of up to 50 maplist completions by the user.
    tags:
    - Users
    - The List
    parameters:
    - in: path
      name: uid
      required: true
      schema:
        type: integer
      description: The user's Discord ID.
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
              type: object
              properties:
                total:
                  type: integer
                  description: The total count of player entries, for pagination.
                completions:
                  type: array
                  description: The player's completions
                  items:
                    $ref: "#/components/schemas/ListCompletionWithMap"
    """
    page = 1
    if "page" in request.query and request.query["page"].isnumeric():
        page = int(request.query["page"])
        if page <= 0:
            page = 1

    completions, count = await get_completions_by(
        request.match_info["uid"],
        idx_start=(page-1)*PAGE_ENTRIES,
        amount=PAGE_ENTRIES,
    )
    return web.json_response({
        "total": count,
        "completions": [cmp.to_dict() for cmp in completions],
    })
