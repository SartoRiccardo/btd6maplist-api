from aiohttp import web
from src.db.queries.completions import get_completion
import http
import src.utils.routedecos
from src.utils.forms import get_submission
from src.db.queries.completions import edit_completion
import src.log


@src.utils.routedecos.bearer_auth
@src.utils.routedecos.validate_resource_exists(get_completion, "cid")
@src.utils.routedecos.with_maplist_profile
@src.utils.routedecos.require_perms()
async def post(
        request: web.Request,
        maplist_profile: dict = None,
        resource: "src.db.models.ListCompletion" = None,
        **_kwargs,
) -> web.Response:
    """
    ---
    description: |
      Accept a completion. Must be a Maplist and/or Expert List Moderator,
      depending on the completion's old and new `format`s.
    tags:
    - Completions
    parameters:
    - in: path
      name: cid
      required: true
      schema:
        type: string
      description: The completion's ID.
    requestBody:
      required: true
      content:
        application/json:
          schema:
            $ref: "#/components/schemas/ListCompletion"
    responses:
      "204":
        description: The completion was accepted
      "400":
        description: |
          One of the fields is badly formatted.
          `data` will be an empty object in this case.
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
      "404":
        description: No completion with that ID was found.
    """
    if resource.accepted:
        return web.json_response(
            {"errors": {"": "This run was already accepted!"}},
            status=http.HTTPStatus.BAD_REQUEST,
        )

    data = await get_submission(request, maplist_profile, resource)
    if isinstance(data, web.Response):
        return data

    await edit_completion(
        resource.id,
        data["black_border"],
        data["no_geraldo"],
        data["format"],
        data["lcc"],
        [int(uid) for uid in data["user_ids"]],
        accept=True,
    )
    await src.log.log_action("completion", "post", resource.id, data, maplist_profile["user"]["id"])
    return web.Response(status=http.HTTPStatus.NO_CONTENT)
