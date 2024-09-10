import http
import json
from aiohttp import web
from typing import Awaitable, Callable, Any
from functools import wraps
from config import MAPLIST_GUILD_ID, MAPLIST_EXPMOD_ID, MAPLIST_LISTMOD_ID, MAPLIST_ADMIN_IDS
import src.http


def validate_json_body(validator_function: Callable[[dict], Awaitable[dict]], **kwargs_deco):
    """Adds `json_body` to kwargs or returns 400."""
    def deco(handler: Callable[[web.Request, Any], Awaitable[web.Response]]):
        @wraps(handler)
        async def wrapper(request: web.Request, *args, **kwargs_caller):
            try:
                body = json.loads(await request.text())
            except json.decoder.JSONDecodeError:
                return web.json_response({"errors": {"": "Invalid JSON data"}, "data": {}}, status=400)

            errors = await validator_function(body, **kwargs_deco)
            if len(errors):
                return web.json_response({"errors": errors, "data": {}}, status=400)
            return await handler(request, *args, **kwargs_caller, json_body=body)
        return wrapper
    return deco


def bearer_auth(handler: Callable[[web.Request, Any], Awaitable[web.Response]]):
    """Adds `token` to kwargs or returns 401."""
    @wraps(handler)
    async def wrapper(request: web.Request, *args, **kwargs):
        if "Authorization" not in request.headers or \
                not request.headers["Authorization"].startswith("Bearer "):
            return web.Response(status=401)
        token = request.headers["Authorization"][len("Bearer "):]
        return await handler(request, *args, **kwargs, token=token)
    return wrapper


def with_maplist_profile(handler: Callable[[web.Request, Any], Awaitable[web.Response]]):
    """
    Must be used with `bearer_auth` beforehand.
    Adds `maplist_profile` to kwargs or returns 401.
    """
    @wraps(handler)
    async def wrapper(request: web.Request, *args, token: str = "", **kwargs):
        if token == "":
            return web.Response(status=401)

        disc_response = await src.http.http.get(
            f"https://discord.com/api/v10/users/@me/guilds/{MAPLIST_GUILD_ID}/member",
            headers={"Authorization": f"Bearer {token}"}
        )
        r = disc_response
        if not disc_response.ok:
            return web.Response(status=401)

        profile = await disc_response.json()
        return await handler(request, *args, **kwargs, token=token, maplist_profile=profile)
    return wrapper


def with_discord_profile(handler: Callable[[web.Request, Any], Awaitable[web.Response]]):
    """
    Must be used with `bearer_auth` beforehand.
    Adds `discord_profile` to kwargs or returns 401.
    """
    @wraps(handler)
    async def wrapper(request: web.Request, *args, token: str = "", **kwargs):
        if token == "":
            return web.Response(status=401)

        disc_response = await src.http.http.get(
            f"https://discord.com/api/v10/users/@me",
            headers={"Authorization": f"Bearer {token}"}
        )
        if not disc_response.ok:
            return web.Response(status=401)

        profile = await disc_response.json()
        return await handler(request, *args, **kwargs, token=token, discord_profile=profile)
    return wrapper


def validate_resource_exists(
        exist_check: Callable[[Any], Awaitable[Any]],
        match_info_key: str,
        **kwargs_deco
):
    """Adds `resource` to kwargs or returns 404."""
    def deco(handler: Callable[[web.Request, Any], Awaitable[web.Response]]):
        @wraps(handler)
        async def wrapper(request: web.Request, *args, **kwargs_caller):
            resource = await exist_check(request.match_info[match_info_key], **kwargs_deco)
            if not resource:
                return web.Response(status=404)
            return await handler(request, *args, **kwargs_caller, resource=resource)
        return wrapper
    return deco


def require_perms(
        list_admin: bool = True,
        explist_admin: bool = True,
):
    """
    Must be used with `with_maplist_profile` beforehand.
    Returns 401 if doesn't have the required perms.
    Adds `is_admin` to kwargs.
    """
    def deco(handler: Callable[[web.Request, Any], Awaitable[web.Response]]):
        @wraps(handler)
        async def wrapper(request: web.Request, *args, **kwargs_caller):
            if "maplist_profile" not in kwargs_caller:
                return web.Response(status=http.HTTPStatus.UNAUTHORIZED)
            mp = kwargs_caller["maplist_profile"]

            is_admin = any([role in MAPLIST_ADMIN_IDS for role in mp["roles"]])
            check_fail = not is_admin
            if list_admin and check_fail:
                check_fail = MAPLIST_LISTMOD_ID not in mp["roles"]
            if explist_admin and check_fail:
                check_fail = MAPLIST_EXPMOD_ID not in mp["roles"]

            if check_fail:
                return web.Response(status=http.HTTPStatus.UNAUTHORIZED)
            return await handler(request, *args, **kwargs_caller, is_admin=is_admin)
        return wrapper
    return deco
