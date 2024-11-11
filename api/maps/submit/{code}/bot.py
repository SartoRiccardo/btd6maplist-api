import asyncio
from aiohttp import web
import http
import src.utils.routedecos
from src.db.queries.mapsubmissions import reject_submission, get_map_submission
from src.utils.embeds import update_map_submission_wh


@src.utils.routedecos.check_bot_signature(path_params=["code"])
@src.utils.routedecos.require_perms()
@src.utils.routedecos.validate_resource_exists(get_map_submission, "code")
async def delete(
        _r: web.Request,
        resource: "src.db.models.MapSubmission" = None,
        json_data: dict = None,
        is_maplist_mod: bool = False,
        is_explist_mod: bool = False,
        **_kwargs,
) -> web.Response:
    if resource.rejected_by is not None:
        return web.json_response(
            {"errors": {"": "This map was already rejected!"}},
            status=http.HTTPStatus.BAD_REQUEST,
        )

    err_str = None
    if resource.for_list == 0 and not is_maplist_mod:
        err_str = "Maplist"
    elif resource.for_list == 1 and not is_explist_mod:
        err_str = "Expert List"
    if err_str:
        return web.json_response(
            {"errors": {"": f"Can't delete a submission to the {err_str} if you're not an {err_str} Mod"}},
            status=http.HTTPStatus.FORBIDDEN,
        )

    await reject_submission(resource.code, json_data["user"]["id"])
    asyncio.create_task(update_map_submission_wh(resource, fail=True))
    return web.Response(status=http.HTTPStatus.NO_CONTENT)
