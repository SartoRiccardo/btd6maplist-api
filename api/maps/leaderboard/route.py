from aiohttp import web
import math
import http
from src.db.queries.leaderboard import get_leaderboard
from src.db.queries.subqueries import LeaderboardType
from typing import get_args
from src.utils.misc import MAPLIST_FORMATS


PAGE_ENTRIES = 50


async def get(request: web.Request):
    """
    ---
    description: Returns the Maplist leaderboard. People with 0 points are omitted.
    tags:
    - Completions
    parameters:
    - in: query
      name: page
      required: false
      schema:
        type: integer
      description: Pagination. Defaults to `1`.
    - in: query
      name: format
      required: false
      schema:
        $ref: "#/components/schemas/MaplistFormat"
      description: The format of the leaderboard to get.
    - in: query
      name: value
      required: false
      schema:
        type: string
        enum: [points, lccs, black_border, no_optimal_hero]
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
    try:
        ml_format = int(request.query.get("format", "1"))
        if ml_format not in MAPLIST_FORMATS:
            return web.json_response(
                {"errors": {"format": f'Allowed values: {", ".join(MAPLIST_FORMATS)}'}},
                status=http.HTTPStatus.BAD_REQUEST,
            )
    except ValueError:
        ml_format = 1

    value = "points"
    if "value" in request.query:
        value = request.query["value"].lower()
        valid_args = get_args(LeaderboardType)
        if value not in valid_args:
            return web.json_response(
                {"error": f"Allowed values for value: {valid_args}"},
                status=http.HTTPStatus.BAD_REQUEST,
            )

    if "page" in request.query and not request.query["page"].isnumeric():
        return web.json_response(
            {"error": '"page" must be a number'},
            status=http.HTTPStatus.BAD_REQUEST,
        )
    page = max(1, int(request.query.get("page", "1")))

    lb, total = await get_leaderboard(
        format=ml_format,
        amount=PAGE_ENTRIES,
        idx_start=PAGE_ENTRIES * (page-1),
        type=value,
    )
    pages = math.ceil(total/PAGE_ENTRIES)

    return web.json_response({
        "total": total,
        "pages": pages,
        "entries": [entry.to_dict() for entry in lb],
    })
