from aiohttp import web
import http
import src.utils.routedecos
from src.db.queries.maps import get_completions_for


PAGE_ENTRIES = 50


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
              type: object
              properties:
                total:
                  type: integer
                  description: The total count of player entries, for pagination.
                completions:
                  type: array
                  items:
                    $ref: "#/components/schemas/ListCompletion"
    """
    page = request.query.get("page")
    if not (page and page.isnumeric()):
        page = 1
    else:
        page = max(1, int(page))

    completions, total = await get_completions_for(
        request.match_info["code"],
        idx_start=PAGE_ENTRIES * (page-1),
        amount=PAGE_ENTRIES,
    )
    return web.json_response({
        "total": total,
        "completions": [cmp.to_dict() for cmp in completions],
    })


@src.utils.routedecos.bearer_auth
@src.utils.routedecos.with_maplist_profile
async def post(
        _r: web.Request,
        maplist_profile: dict = None
) -> web.Response:
    return web.Response(status=http.HTTPStatus.NOT_IMPLEMENTED)
