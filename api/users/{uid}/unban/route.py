import http
from aiohttp import web
import src.utils.routedecos
from src.db.queries.users import unban_user
from src.exceptions import MissingPermsException


@src.utils.routedecos.bearer_auth
@src.utils.routedecos.with_discord_profile
@src.utils.routedecos.require_perms()
async def post(
        request: web.Request,
        permissions: "src.db.models.Permissions" = None,
        **_kwargs,
) -> web.Response:
    """
    ---
    description: Unban a user. Must have ban:user.
    tags:
    - Users
    responses:
      "204":
        description: The user was unbanned successfully
      "401":
        description: Your token is missing or invalid
      "403":
        description: You don't have the permissions to do this
    """
    if not permissions.has_in_any("ban:user"):
        raise MissingPermsException("ban:user")

    user_id = request.match_info.get("uid", "0")
    if user_id.isnumeric():
        await unban_user(user_id)

    return web.Response(status=http.HTTPStatus.NO_CONTENT)
