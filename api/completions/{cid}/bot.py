import asyncio
from aiohttp import web
from src.db.queries.completions import get_completion
import http
import src.utils.routedecos
from src.db.queries.completions import delete_completion
import src.log
from src.utils.embeds import update_run_webhook


@src.utils.routedecos.check_bot_signature(path_params=["cid"])
@src.utils.routedecos.validate_resource_exists(get_completion, "cid")
async def delete(
        _r: web.Request,
        resource: "src.db.models.ListCompletionWithMeta" = None,
        json_data: dict = None,
        **_kwargs,
) -> web.Response:
    """Only deletes if not `accepted_by`"""
    if resource.accepted_by is not None:
        return web.json_response(
            {"errors": {"": "This run was already accepted!"}},
            status=http.HTTPStatus.BAD_REQUEST,
        )

    profile = json_data["user"]
    await delete_completion(resource.id, hard_delete=True)
    asyncio.create_task(update_run_webhook(resource, fail=True))

    asyncio.create_task(src.log.log_action("completion", "delete", resource.id, None, profile["id"]))
    return web.Response(status=http.HTTPStatus.NO_CONTENT)