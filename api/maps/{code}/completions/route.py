from aiohttp import web
import math
import http
import src.log
import src.utils.routedecos
from src.db.queries.maps import get_map
from src.db.queries.maps import get_completions_for
from src.db.queries.completions import add_completion
from src.utils.forms import get_submission


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
                  description: The total count of player entries.
                pages:
                  type: integer
                  description: The total number of pages.
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
        "pages": math.ceil(total/PAGE_ENTRIES),
        "completions": [cmp.to_dict() for cmp in completions],
    })


@src.utils.routedecos.bearer_auth
@src.utils.routedecos.validate_resource_exists(get_map, "code", partial=True)
@src.utils.routedecos.with_maplist_profile
async def post(
        request: web.Request,
        maplist_profile: dict = None,
        resource: "src.db.model.PartialMap" = None,
        **_kwargs,
) -> web.Response:
    """
    ---
    description: |
      Add a completion. Must be a Maplist and/or Expert List Moderator,
      depending on the completion's `format`s.
    tags:
    - Completions
    parameters:
    - in: path
      name: code
      required: true
      schema:
        type: string
      description: The map's code to add the completion to.
    requestBody:
      required: true
      content:
        application/json:
          schema:
            $ref: "#/components/schemas/ListCompletion"
    responses:
      "200":
        description: The resource was added.
        content:
          application/json:
            schema:
              type: array
              description: The Discord ID of the added users.
              items:
                $ref: "#/components/schemas/DiscordID"
      "400":
        description: |
          One of the fields is badly formatted.
          `data` will be an empty array in this case.
        content:
          application/json:
            schema:
              type: object
              properties:
                errors:
                  type: object
                  description: Each key-value pair is the key of the wrong field and a description as to why.
                data:
                  type: object
                  example: {}
      "401":
        description: Your token is missing, invalid or you don't have the privileges for this.
    """
    data = await get_submission(request, maplist_profile)
    if isinstance(data, web.Response):
        return data

    await add_completion(
        resource.code,
        data["black_border"],
        data["no_geraldo"],
        data["format"],
        data["lcc"],
        [int(uid) for uid in data["user_ids"]],
    )
    await src.log.log_action("completion", "post", resource.id, data, maplist_profile["user"]["id"])

    return web.json_response(
        data["user_ids"],
        status=http.HTTPStatus.OK,
    )
