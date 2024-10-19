import math
from aiohttp import web
from src.db.queries.completions import get_unapproved_completions


PAGE_ENTRIES = 50


async def get(request: web.Request) -> web.Response:
    """
    ---
    description: |
      Returns a list of unapproved runs. Unlike other completion endpoints,
      this returns runs of all formats.
    tags:
    - Completions
    parameters:
    - in: query
      name: page
      required: false
      schema:
        type: integer
      description: Pagination. Defaults to `1`.
    responses:
      "200":
        description: Returns an array of `ListCompletionWithMeta`.
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
                  description: The unapproved completions.
                  items:
                    $ref: "#/components/schemas/ListCompletionWithMeta"
    """
    page = request.query.get("page")
    if not (page and page.isnumeric()):
        page = 1
    else:
        page = max(1, int(page))

    completions, count = await get_unapproved_completions(
        idx_start=(page-1)*PAGE_ENTRIES,
        amount=PAGE_ENTRIES,
    )
    return web.json_response({
        "total": count,
        "pages": math.ceil(count/PAGE_ENTRIES),
        "completions": [cmp.to_dict() for cmp in completions],
    })
