import asyncio
import json
from aiohttp import web
import http
import src.log
import src.http
from src.db.queries.mapsubmissions import reject_submission, get_map_submission, add_map_submission_wh
from src.utils.forms import get_map_form
from src.utils.embeds import FAIL_CLR
import src.utils.routedecos
from config import WEBHOOK_LIST_SUBM, WEBHOOK_EXPLIST_SUBM


@src.utils.routedecos.bearer_auth
@src.utils.routedecos.validate_resource_exists(get_map_submission, "code")
@src.utils.routedecos.with_maplist_profile
@src.utils.routedecos.require_perms()
async def delete(
        request: web.Request,
        resource: "src.db.model.MapSubmission" = None,
        maplist_profile: dict = None,
        **_kwargs,
):
    """
    ---
    description: |
      Soft deletes a map submission. Must be a Maplist or Expert List Moderator.
    tags:
    - The List
    - Expert List
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
        description: Your token is missing, invalid or you don't have the privileges for this.
      "404":
        description: No map with that ID was found.
    """
    if resource.rejected_by:
        return web.Response(status=http.HTTPStatus.NO_CONTENT)
    code = request.match_info["code"]

    async def update_submission_wh():
        if resource.wh_data is None:
            return
        hook_url = [WEBHOOK_LIST_SUBM, WEBHOOK_EXPLIST_SUBM][resource.for_list]
        msg_id, wh_data = resource.wh_data.split(";", 1)
        wh_data = json.loads(wh_data)
        wh_data["embeds"][0]["color"] = FAIL_CLR
        async with src.http.http.patch(hook_url + f"/messages/{msg_id}", json=wh_data) as resp:
            if resp.ok:
                await add_map_submission_wh(code, None)

    await reject_submission(code, maplist_profile["user"]["id"])
    asyncio.create_task(update_submission_wh())
    return web.Response(status=http.HTTPStatus.NO_CONTENT)
