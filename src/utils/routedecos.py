import json
from aiohttp import web
from typing import Awaitable, Callable, Any
from functools import wraps
from config import MAPLIST_GUILD_ID
import src.http


def validate_json_body(validator_function: Callable[[dict], Awaitable[dict]]):
    """Adds `json_body` to kwargs or returns 400."""
    def deco(handler: Callable[[web.Request, Any], Awaitable[web.Response]]):
        @wraps(handler)
        async def wrapper(request: web.Request, *args, **kwargs):
            try:
                body = json.loads(await request.text())
            except json.decoder.JSONDecodeError:
                return web.json_response({"errors": {"": "Invalid JSON data"}, "data": {}}, status=400)

            errors = await validator_function(body)
            if len(errors):
                return web.json_response({"errors": errors, "data": {}}, status=400)
            return await handler(request, *args, json_body=body, **kwargs)
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
        return await handler(request, *args, token=token, **kwargs)
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
        if not disc_response.ok:
            return web.Response(status=401)

        profile = await disc_response.json()
        return await handler(request, *args, token=token, maplist_profile=profile, **kwargs)
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
        return await handler(request, *args, token=token, discord_profile=profile, **kwargs)
    return wrapper