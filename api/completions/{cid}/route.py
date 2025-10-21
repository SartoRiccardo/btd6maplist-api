from aiohttp import web
import asyncio
import http
from src.db.queries.completions import get_completion, edit_completion, delete_completion
from src.utils.validators import validate_completion
import src.utils.routedecos
from src.utils.forms import get_completion_request
from src.utils.embeds import update_run_webhook
import src.log


@src.utils.routedecos.validate_resource_exists(get_completion, "cid")
async def get(_r: web.Request, resource: "src.db.models.ListCompletionWithMeta" = None):
    """
    ---
    description: Returns a completion's data.
    tags:
    - Completions
    parameters:
    - in: path
      name: cid
      required: true
      schema:
        type: string
      description: The completion's ID.
    responses:
      "200":
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/ListCompletionWithMeta"
      "404":
        description: No code with that ID was found.
    """
    return web.json_response(resource.to_dict())


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
      Edit a completion. Must be a Maplist and/or Expert List Moderator,
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
            $ref: "#/components/schemas/ListCompletionPayload"
    responses:
      "204":
        description: The resource was modified correctly
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
      "404":
        description: No completion with that ID was found.
    """
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
    )
    asyncio.create_task(src.log.log_action("completion", "put", resource.id, data, discord_profile["id"]))
    return web.Response(status=http.HTTPStatus.NO_CONTENT)


@src.utils.routedecos.bearer_auth
@src.utils.routedecos.validate_resource_exists(get_completion, "cid")
@src.utils.routedecos.with_discord_profile
@src.utils.routedecos.require_perms()
async def delete(
        _r: web.Request,
        discord_profile: dict = None,
        resource: "src.db.models.ListCompletionWithMeta" = None,
        permissions: "src.db.models.Permissions" = None,
        **_kwargs,
) -> web.Response:
    """
    ---
    description: |
      Soft deletes a completion. Must have delete:completion permissions.
      Deleted completions and all their data are kept in the database, but ignored.
    tags:
    - Completions
    parameters:
    - in: path
      name: cid
      required: true
      schema:
        type: string
      description: The completion's ID.
    responses:
      "204":
        description: The resource was deleted correctly
      "401":
        description: Your token is missing, invalid, or you don't have the privileges for this.
      "404":
        description: No map with that ID was found.
    """
    if not permissions.has("delete:completion", resource.format):
        return web.json_response(
            {"errors": {"format": f"You are missing `delete:completion` on format {resource.format}"}},
            status=http.HTTPStatus.FORBIDDEN,
        )

    if not resource.deleted_on:
        reject = resource.accepted_by is None
        if reject:
            asyncio.create_task(update_run_webhook(resource, fail=True))
        await delete_completion(resource.id, hard_delete=False)
        asyncio.create_task(src.log.log_action("completion", "delete", resource.id, None, discord_profile["id"]))

    return web.Response(status=http.HTTPStatus.NO_CONTENT)
