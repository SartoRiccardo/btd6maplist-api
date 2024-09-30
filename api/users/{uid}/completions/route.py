from aiohttp import web
import math
from src.db.queries.users import get_completions_by


PAGE_ENTRIES = 50


async def get(request: web.Request):
    """
    ---
    description: Returns a list of up to 50 maplist completions by the user.
    tags:
    - Users
    - Completions
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
                pages:
                  type: integer
                  description: The total number of pages.
                completions:
                  type: array
                  description: The player's completions
                  items:
                    $ref: "#/components/schemas/ListCompletionWithMap"
    """
    page = request.query.get("page")
    if not (page and page.isnumeric()):
        page = 1
    else:
        page = max(1, int(page))

    formats = [int(fmt) for fmt in request.query.get("formats", "1,51").split(",") if fmt.isnumeric()]

    completions, count = await get_completions_by(
        request.match_info["uid"],
        formats,
        idx_start=(page-1)*PAGE_ENTRIES,
        amount=PAGE_ENTRIES,
    )
    return web.json_response({
        "total": count,
        "pages": math.ceil(count/PAGE_ENTRIES),
        "completions": [cmp.to_dict() for cmp in completions],
    })
