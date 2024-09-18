import asyncio
from aiohttp import web
from src.db.queries.completions import get_completion
import http
import src.utils.routedecos
from src.db.queries.completions import accept_completion
import src.log
from src.utils.embeds import update_run_webhook


@src.utils.routedecos.check_bot_signature(path_params=["cid"])
@src.utils.routedecos.validate_resource_exists(get_completion, "cid")
async def post(
        _r: web.Request,
        resource: "src.db.models.ListCompletion" = None,
        json_data: dict = None,
        **_kwargs,
) -> web.Response:
    """Only sets `accepted`"""
    if resource.accepted_by is not None:
        return web.json_response(
            {"errors": {"": "This run was already accepted!"}},
            status=http.HTTPStatus.BAD_REQUEST,
        )

    profile = json_data["user"]

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
            "proof_completion": resource.lcc.proof,
        },
        "format": resource.format,
    }
    if resource.lcc is not None:
        dict_res["proof"] = resource.lcc.proof
    await src.log.log_action("completion", "post", resource.id, dict_res, profile["id"])
    return web.Response(status=http.HTTPStatus.NO_CONTENT)
