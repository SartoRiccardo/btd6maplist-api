import asyncio
from aiohttp import web
import http
import src.log
import src.http
from src.db.queries.mapsubmissions import reject_submission, get_map_submission
from src.utils.forms import get_map_form
from src.utils.embeds import update_map_submission_wh
import src.utils.routedecos


@src.utils.routedecos.bearer_auth
@src.utils.routedecos.validate_resource_exists(get_map_submission, "code")
@src.utils.routedecos.with_discord_profile
@src.utils.routedecos.require_perms()
async def delete(
        request: web.Request,
        resource: "src.db.model.MapSubmission" = None,
        discord_profile: dict = None,
        permissions: "src.db.models.Permissions" = None,
        **_kwargs,
):
    """
    ---
    description: |
      Soft deletes a map submission. Must be a Maplist or Expert List Moderator.
    tags:
    - Submissions
    parameters:
    - in: path
      name: code
      required: true
      schema:
        type: string
      description: The map's code.
    responses:
      "204":
        description: The resource was deleted correctly
      "401":
        description: Your token is missing or invalid.
      "403":
        description: You don't have the privileges for this.
      "404":
        description: No map submission with that code was found.
    """
    if resource.rejected_by:
        return web.Response(status=http.HTTPStatus.NO_CONTENT)
    code = request.match_info["code"]

    if not permissions.has("delete:map_submission", resource.for_list):
        return web.json_response(
            {"errors": {"": f"You are missing `delete:map_submission` on format {resource.for_list}"}},
            status=http.HTTPStatus.FORBIDDEN,
        )

    await reject_submission(code, discord_profile["id"])
    asyncio.create_task(update_map_submission_wh(resource, fail=True))
    return web.Response(status=http.HTTPStatus.NO_CONTENT)
