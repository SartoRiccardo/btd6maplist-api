import http
from aiohttp import web
from typing import get_args
from src.utils.types import SearchEntity
from src.db.queries.search import search
from src.db.models import PartialMap, PartialUser

LIMIT_DEFAULT = 5
MIN_Q_LENGTH = 1


async def get(
        request: web.Request,
) -> web.Response:
    """
    ---
    description: Searches a resource in the database.
    tags:
    - Search
    parameters:
    - in: query
      name: q
      required: true
      schema:
        type: string
      description: The query to search for. Must not be empty.
    - in: query
      name: type
      required: false
      schema:
        type: array
        items:
          type: string
          enum: [user, map]
      description: The entities to get, comma-separated. Defaults to `user,map`.
    - in: query
      name: limit
      required: false
      schema:
        type: integer
      description: The max amount of records to return. Defaults to `5`, can't be higher than `50`.
    responses:
      "200":
        description: Returns an array of search results.
        content:
          application/json:
            schema:
              type: array
              properties:
              items:
                type: object
                properties:
                  type:
                    type: string
                    enum: [user, map]
                  data:
                    oneOf:
                    - $ref: "#/components/schemas/PartialListMap"
                    - $ref: "#/components/schemas/PartialUser"
      "400":
        description: Invalid request, the error will be specified in the `error` key.
    """
    if "q" not in request.query:
        return web.json_response(
            {"errors": {"q": "Missing search parameter"}},
            status=http.HTTPStatus.BAD_REQUEST,
        )
    elif len(request.query["q"]) < MIN_Q_LENGTH:
        return web.json_response(
            {"errors": {"q": f"Search query must be at least {MIN_Q_LENGTH} characters"}},
            status=http.HTTPStatus.BAD_REQUEST,
        )

    entities = get_args(SearchEntity)
    req_entities = request.query.get("type", "user").split(",")
    for i in range(len(req_entities)-1, -1, -1):
        if req_entities[i] not in entities:
            req_entities.pop(i)

    try:
        limit = min(50, int(request.query.get("limit", str(LIMIT_DEFAULT))))
    except ValueError:
        limit = LIMIT_DEFAULT

    types_str = {
        PartialUser: "user",
        PartialMap: "map",
    }

    results = await search(request.query["q"], req_entities, limit)
    return web.json_response([
        {"type": types_str[type(res)], "data": res.to_dict()}
        for _s, res in results
    ])
