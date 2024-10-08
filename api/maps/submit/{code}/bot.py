import asyncio
from aiohttp import web
import http
import src.utils.routedecos
from src.db.queries.mapsubmissions import reject_submission, get_map_submission
from src.utils.embeds import update_map_submission_wh


@src.utils.routedecos.check_bot_signature(path_params=["code"])
@src.utils.routedecos.validate_resource_exists(get_map_submission, "code")
async def delete(
        _r: web.Request,
        resource: "src.db.models.MapSubmission" = None,
        json_data: dict = None,
        **_kwargs,
) -> web.Response:
    if resource.rejected_by is not None:
        return web.json_response(
            {"errors": {"": "This map was already rejected!"}},
            status=http.HTTPStatus.BAD_REQUEST,
        )

    await reject_submission(resource.code, json_data["user"]["id"])
    asyncio.create_task(update_map_submission_wh(resource, fail=True))
    return web.Response(status=http.HTTPStatus.NO_CONTENT)
