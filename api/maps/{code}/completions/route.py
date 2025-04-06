import asyncio
from aiohttp import web
import math
import http
import src.log
import src.utils.routedecos
from src.db.queries.maps import get_map
from src.db.queries.maps import get_completions_for
from src.db.queries.completions import add_completion
from src.utils.forms import get_completion_request

PAGE_ENTRIES = 50


@src.utils.routedecos.validate_resource_exists(get_map, "code", partial=True)
async def get(
        request: web.Request,
        **kwargs,
) -> web.Response:
    """
    ---
    description: Returns a list of up to 50 maplist completions of this map.
    tags:
    - Completions
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
    - in: query
      name: formats
      required: false
      schema:
        type: list
      description: Formats to show. Defaults to `1,51`.
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

    formats = [int(fmt) for fmt in request.query.get("formats", "1,51").split(",") if fmt.isnumeric()]

    completions, total = await get_completions_for(
        request.match_info["code"],
        formats,
        idx_start=PAGE_ENTRIES * (page-1),
        amount=PAGE_ENTRIES,
    )
    return web.json_response({
        "total": total,
        "pages": math.ceil(total/PAGE_ENTRIES),
        "completions": [cmp.to_dict() for cmp in completions],
    })


@src.utils.routedecos.bearer_auth
@src.utils.routedecos.with_discord_profile
@src.utils.routedecos.require_perms()
@src.utils.routedecos.validate_resource_exists(get_map, "code", partial=True)
async def post(
        request: web.Request,
        discord_profile: dict = None,
        resource: "src.db.model.PartialMap" = None,
        permissions: "src.db.models.Permissions" = None,
        **_kwargs,
) -> web.Response:
    """
    ---
    description: |
      Add a completion. Must have create:completion perms.
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
        multipart/form-data:
          schema:
            type: object
            required: [data]
            properties:
              data:
                $ref: "#/components/schemas/ListCompletionPayload"
              submission_proof:
                type: string
                format: binary
        application/json:
          schema:
            $ref: "#/components/schemas/ListCompletionPayload"
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
        description: Your token is missing, invalid, or you don't have the privileges for this.
    """
    data = await get_completion_request(
        request,
        discord_profile["id"],
        permissions=permissions,
    )
    if isinstance(data, web.Response):
        return data

    comp_id = await add_completion(
        resource.code,
        data["black_border"],
        data["no_geraldo"],
        data["format"],
        data["lcc"],
        [int(uid) for uid in data["user_ids"]],
        int(discord_profile["id"]),
        subm_proof=data["subm_proof"],
    )
    asyncio.create_task(src.log.log_action("completion", "post", resource.id, data, discord_profile["id"]))

    return web.json_response(
        data["user_ids"],
        status=http.HTTPStatus.CREATED,
        headers={"Location": f"/completions/{comp_id}"},
    )
