from aiohttp import web
from src.db.queries.leaderboard import (
    get_maplist_leaderboard,
    get_maplist_lcc_leaderboard,
)


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
                status=400,
            )

    value = "points"
    if "value" in request.query:
        value = request.query["value"].lower()
        if value not in ["points", "lccs"]:
            return web.json_response(
                {
                    "error": 'Allowed values for "value": ["points", "lccs"]'
                },
                status=400,
            )

    if value == "points":
        lb = await get_maplist_leaderboard(curver=current_version)
    else:
        lb = await get_maplist_lcc_leaderboard(curver=current_version)
    return web.json_response([entry.to_dict() for entry in lb])
