import asyncio
from aiohttp import web
import http
import src.utils.routedecos
from src.db.queries.mapsubmissions import reject_submission, get_map_submission
from src.utils.embeds import update_map_submission_wh
from src.exceptions import GenericErrorException, MissingPermsException


@src.utils.routedecos.check_bot_signature(path_params=["code"])
@src.utils.routedecos.require_perms()
@src.utils.routedecos.validate_resource_exists(get_map_submission, "code", "format_id")
async def delete(
        _r: web.Request,
        resource: "src.db.models.MapSubmission" = None,
        json_data: dict = None,
        permissions: "src.db.models.Permissions" = None,
        **_kwargs,
) -> web.Response:
    if resource.rejected_by is not None:
        raise GenericErrorException("This map was already rejected!")

    if not permissions.has("delete:map_submission", resource.format_id):
        raise MissingPermsException("delete:map_submission", resource.format_id)

    await reject_submission(resource.code, resource.format_id, json_data["user"]["id"])
    asyncio.create_task(update_map_submission_wh(resource, fail=True))
    return web.Response(status=http.HTTPStatus.NO_CONTENT)
