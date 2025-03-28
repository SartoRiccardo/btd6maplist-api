import asyncio
from aiohttp import web
from src.db.queries.completions import get_completion
import http
import src.utils.routedecos
from src.db.queries.completions import accept_completion
import src.log
from src.utils.validators import validate_completion_perms
from src.utils.embeds import update_run_webhook
from src.exceptions import GenericErrorException


@src.utils.routedecos.check_bot_signature(path_params=["cid"])
@src.utils.routedecos.require_perms()
@src.utils.routedecos.validate_resource_exists(get_completion, "cid")
async def put(
        _r: web.Request,
        resource: "src.db.models.ListCompletion" = None,
        json_data: dict = None,
        permissions: "src.db.models.Permissions" = None,
        **_kwargs,
) -> web.Response:
    """Only sets `accepted_by`"""
    if resource.accepted_by is not None:
        raise GenericErrorException("This run was already accepted!", status_code=http.HTTPStatus.BAD_REQUEST)

    err_resp = validate_completion_perms(
        permissions,
        resource.format,
        action="edit",
    )
    if isinstance(err_resp, web.Response):
        return err_resp

    profile = json_data["user"]
    if int(profile["id"]) in [x if isinstance(x, int) else x.id for x in resource.user_ids]:
        raise GenericErrorException("Cannot edit or accept your own completion", status_code=http.HTTPStatus.FORBIDDEN)

    await accept_completion(resource.id, int(profile["id"]))
    asyncio.create_task(update_run_webhook(resource))

    dict_res = {
        "accept": True,
        "black_border": resource.black_border,
        "no_geraldo": resource.black_border,
        "user_ids": [
            str(u) if isinstance(u, int) else str(u.id)
            for u in resource.user_ids
        ],
        "lcc": None if resource.lcc is None else {
            "leftover": resource.lcc.leftover,
        },
        "format": resource.format,
    }
    asyncio.create_task(src.log.log_action("completion", "post", resource.id, dict_res, profile["id"]))
    return web.Response(status=http.HTTPStatus.NO_CONTENT)
