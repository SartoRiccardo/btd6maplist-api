from aiohttp import web
import math
import http
from src.db.queries.leaderboard import (
    get_maplist_leaderboard,
    get_maplist_lcc_leaderboard,
)


PAGE_ENTRIES = 50


async def get(request: web.Request):
    """
    ---
    description: Returns the Maplist leaderboard. People with 0 points are omitted.
    tags:
    - The List
    parameters:
    - in: query
      name: page
      required: false
      schema:
        type: integer
      description: Pagination. Defaults to `1`.
    - in: query
      name: version
      required: false
      schema:
        type: string
        enum: [current, all]
      description: The format of the leaderboard to get.
    - in: query
      name: value
      required: false
      schema:
        type: string
        enum: [points, lccs]
      description: The type of leaderboard to get.
    responses:
      "200":
        description: Returns an array of `LeaderboardEntry`.
        content:
          application/json:
            schema:
              type: object
              properties:
                total:
                  type: integer
                  description: The total count of player entries.
                pages:
                  type: integer
                  description: The total number of pages.
                entries:
                  type: array
                  items:
                    $ref: "#/components/schemas/LeaderboardEntry"
    """
    current_version = True
    if "version" in request.query:
        version = request.query["version"].lower()
        if version.lower() == "all":
            current_version = False
        elif version != "current":
            return web.json_response(
                {
                    "error": 'Allowed values for "version": ["current", "all"]'
                },
                status=http.HTTPStatus.BAD_REQUEST,
            )

    value = "points"
    if "value" in request.query:
        value = request.query["value"].lower()
        if value not in ["points", "lccs"]:
            return web.json_response(
                {
                    "error": 'Allowed values for "value": ["points", "lccs"]'
                },
                status=http.HTTPStatus.BAD_REQUEST,
            )

    if "page" in request.query and not request.query["page"].isnumeric():
        return web.json_response(
            {
                "error": '"page" must be a number'
            },
            status=http.HTTPStatus.BAD_REQUEST,
        )
    page = max(1, int(request.query.get("page", "1")))

    pages = 1
    if value == "points":
        lb, total = await get_maplist_leaderboard(
            curver=current_version,
            amount=PAGE_ENTRIES,
            idx_start=PAGE_ENTRIES * (page-1),
        )
        pages = math.ceil(total/PAGE_ENTRIES)
    else:
        lb, total = await get_maplist_lcc_leaderboard(curver=current_version)

    return web.json_response({
        "total": total,
        "pages": pages,
        "entries": [entry.to_dict() for entry in lb],
    })
