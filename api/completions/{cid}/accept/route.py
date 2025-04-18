import asyncio
from aiohttp import web
from src.db.queries.completions import get_completion
import http
import src.utils.routedecos
from src.utils.forms import get_completion_request
from src.utils.embeds import update_run_webhook
from src.db.queries.completions import edit_completion
import src.log


@src.utils.routedecos.bearer_auth
@src.utils.routedecos.validate_resource_exists(get_completion, "cid")
@src.utils.routedecos.with_discord_profile
@src.utils.routedecos.require_perms()
async def put(
        request: web.Request,
        discord_profile: dict = None,
        resource: "src.db.models.ListCompletionWithMeta" = None,
        permissions: "src.db.models.Permissions" = None,
        **_kwargs,
) -> web.Response:
    """
    ---
    description: |
      Accept a completion. Must be a Maplist and/or Expert List Moderator,
      depending on the completion's old and new `format`s.
    tags:
    - Submissions
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
            $ref: "#/components/schemas/ListCompletionPayload"
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
    if resource.accepted_by is not None:
        return web.json_response(
            {"errors": {"": "This run was already accepted!"}},
            status=http.HTTPStatus.BAD_REQUEST,
        )

    data = await get_completion_request(
        request,
        discord_profile["id"],
        permissions=permissions,
        resource=resource,
    )
    if isinstance(data, web.Response):
        return data

    await edit_completion(
        resource.id,
        data["black_border"],
        data["no_geraldo"],
        data["format"],
        data["lcc"],
        [int(uid) for uid in data["user_ids"]],
        accept=int(discord_profile["id"]),
    )
    asyncio.create_task(update_run_webhook(resource))
    asyncio.create_task(src.log.log_action("completion", "post", resource.id, data, discord_profile["id"]))
    return web.Response(status=http.HTTPStatus.NO_CONTENT)
