from aiohttp import web
import math
import src.utils.routedecos
from src.db.queries.users import get_completions_by, get_user_min

PAGE_ENTRIES = 50


@src.utils.routedecos.validate_resource_exists(get_user_min, "uid")
async def get(
        request: web.Request,
        **kwargs,
) -> web.Response:
    """
    ---
    description: Returns a list of up to 50 maplist completions by the user.
    tags:
    - Completions
    parameters:
    - in: path
      name: uid
      required: true
      schema:
        type: integer
      description: The user's Discord ID.
    - in: query
      name: formats
      required: false
      schema:
        type: list
      description: Formats to show. Defaults to `1,51`.
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
                    allOf:
                    - $ref: "#/components/schemas/ListCompletionWithMap"
                    - type: object
                      properties:
                        users:
                          type: array
                          items:
                            $ref: "#/components/schemas/DiscordID"
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
