import http
import json
import random
import string
import aiohttp
import base64
import cryptography.exceptions
from aiohttp import web
from typing import Awaitable, Callable, Any
from functools import wraps
import src.http
from src.db.queries.users import create_user, get_user_min, get_user_perms
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from ..requests import discord_api
from src.exceptions import GenericErrorException, ValidationException


def validate_json_body(validator_function: Callable[[dict], Awaitable[dict]], **kwargs_deco):
    """Adds `json_body` to kwargs or returns 400."""
    def deco(handler: Callable[[web.Request, Any], Awaitable[web.Response]]):
        @wraps(handler)
        async def wrapper(request: web.Request, *args, **kwargs_caller):
            try:
                body = json.loads(await request.text())
            except json.decoder.JSONDecodeError:
                raise GenericErrorException("Invalid JSON data", status_code=http.HTTPStatus.BAD_REQUEST)

            if errors := await validator_function(body, **kwargs_deco):
                raise ValidationException(errors)
            return await handler(request, *args, **kwargs_caller, json_body=body)
        return wrapper
    return deco


def bearer_auth(handler: Callable[[web.Request, Any], Awaitable[web.Response]]):
    """Adds `token` to kwargs or returns 401."""
    @wraps(handler)
    async def wrapper(request: web.Request, *args, **kwargs):
        if "Authorization" not in request.headers or \
                not request.headers["Authorization"].startswith("Bearer "):
            raise GenericErrorException("No token found", status_code=http.HTTPStatus.UNAUTHORIZED)
        token = request.headers["Authorization"][len("Bearer "):]
        return await handler(request, *args, **kwargs, token=token)
    return wrapper


def with_discord_profile(handler: Callable[[web.Request, Any], Awaitable[web.Response]]):
    """
    Must be used with `bearer_auth` beforehand.
    TODO Migrate to JWT and dont call an external service every auth call
    Adds `discord_profile` to kwargs or returns 401.
    """
    @wraps(handler)
    async def wrapper(request: web.Request, *args, token: str = "", **kwargs):
        if token == "":
            raise GenericErrorException("No Discord token found", status_code=http.HTTPStatus.UNAUTHORIZED)

        try:
            profile = await discord_api().get_user_profile(token)
            return await handler(request, *args, **kwargs, token=token, discord_profile=profile)
        except aiohttp.ClientResponseError:
            raise GenericErrorException("Couldn't verify your Discord account", status_code=http.HTTPStatus.UNAUTHORIZED)

    return wrapper


def validate_resource_exists(
        exist_check: Callable[[Any], Awaitable[Any]],
        *match_info_key: str,
        **kwargs_deco
):
    """Adds `resource` to kwargs or returns 404."""
    def deco(handler: Callable[[web.Request, Any], Awaitable[web.Response]]):
        @wraps(handler)
        async def wrapper(request: web.Request, *args, **kwargs_caller):
            args_get = [request.match_info[key] for key in match_info_key]
            resource = await exist_check(*args_get, **kwargs_deco)
            if not resource:
                return web.Response(status=http.HTTPStatus.NOT_FOUND)
            return await handler(request, *args, **kwargs_caller, resource=resource)
        return wrapper
    return deco


def require_perms():
    """
    Must be used with `with_discord_profile` or `check_bot_signature` beforehand.
    Returns 403 if they don't have any perms, adds `permissions` to kwargs othewise.
    """
    def deco(handler: Callable[[web.Request, Any], Awaitable[web.Response]]):
        @wraps(handler)
        async def wrapper(request: web.Request, *args, **kwargs_caller):
            discord_profile = None
            if "discord_profile" in kwargs_caller:
                discord_profile = kwargs_caller["discord_profile"]
            elif "json_data" in kwargs_caller:
                discord_profile = kwargs_caller["json_data"]["user"]
            if discord_profile is None:
                return web.Response(status=http.HTTPStatus.UNAUTHORIZED)
            permissions = await get_user_perms(discord_profile["id"])

            return await handler(
                request,
                *args,
                **kwargs_caller,
                permissions=permissions,
            )
        return wrapper
    return deco


def register_user(handler: Callable[[web.Request, Any], Awaitable[web.Response]]):
    """
    Must be used with `with_maplist_profile`, `check_bot_signature`, or `with_discord_profile` beforehand.
    Adds a user to the dabatase if it's not there already.
    """
    @wraps(handler)
    async def wrapper(request: web.Request, *args, **kwargs_caller):
        profile = None
        if "maplist_profile" in kwargs_caller:
            profile = kwargs_caller["maplist_profile"]["user"]
        elif "discord_profile" in kwargs_caller:
            profile = kwargs_caller["discord_profile"]
        elif "json_data" in kwargs_caller:
            profile = kwargs_caller["json_data"]["user"]

        if profile is None:
            return web.Response(status=http.HTTPStatus.INTERNAL_SERVER_ERROR)

        possible_user = await get_user_min(profile["id"])
        if not possible_user or possible_user.id != profile["id"]:
            success = await create_user(profile["id"], profile["username"], if_not_exists=True)
            if not success:
                rand = random.choices(string.ascii_letters, k=10)
                await create_user(profile["id"], profile["username"]+f"-{rand}", if_not_exists=True)

        return await handler(request, *args, **kwargs_caller)
    return wrapper


# https://cryptography.io/en/latest/hazmat/primitives/asymmetric/rsa/#verification
def _check_signature(signature: bytes, message: bytes) -> None:
    src.http.bot_pubkey.verify(
        signature,
        message,
        padding=padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        algorithm=hashes.SHA256(),
    )


def check_bot_signature(
        files: list[str] | None = None,
        path_params: list[str] | None = None,
        qparams: list[str] | None = None,
        no_content: bool = False,
):
    """
    Checks the bot's signature.
    To craft a message, one must chain (in order):
    - Path parameters, in the specified order
    - Query parameters, in the specified order
    - The json content, present in body.data
    - File contents, in the specified order

    If no_content, checks the signature before getting to the body. The signature
    must be present in the "signature" query parameter.
    Otherwise, checks also the body and adds `files: list[tuple[str, bytes]]` and
    `json_data: dict` to kwargs.

    Returns 403 if the signature doesn't match.

    Bot usually routes assume most data is already validated by the bot.
    :param files: List of valid filenames, in order.
    :param path_params: List of path parameter keys.
    :param qparams: List of query parameter keys.
    :param no_content: Whether the request has no content.
    """
    files = files if files is not None else []
    qparams = qparams if qparams is not None else []
    path_params = path_params if path_params is not None else []

    def deco(handler):
        @wraps(handler)
        async def wrapper(request: web.Request, *args, **kwargs):
            message = b""
            for pp in path_params:
                message += request.match_info[pp].encode()
            for qp in qparams:
                message += request.query.get(qp, "").encode()

            if no_content:
                if "signature" not in request.query:
                    return web.Response(status=http.HTTPStatus.UNAUTHORIZED)
                signature = base64.b64decode(request.query["signature"].encode())
                try:
                    _check_signature(signature, message)
                except cryptography.exceptions.InvalidSignature:
                    return web.Response(status=http.HTTPStatus.FORBIDDEN)
                return await handler(request, *args, **kwargs)

            req_files: list[tuple[str, bytes] | None] = [None for _ in range(len(files))]
            req_data = None

            if request.content_type == "application/json":
                req_data = json.loads(await request.text())
            else:
                reader = await request.multipart()
                while part := await reader.next():
                    if part.name == "data":
                        req_data = await part.json()
                    elif part.name in files:
                        fext = part.headers[aiohttp.hdrs.CONTENT_TYPE].split("/")[-1]
                        file_idx = files.index(part.name)
                        req_files[file_idx] = (f"{part.name}.{fext}", await part.read(decode=False))

            if req_data is None or "signature" not in req_data or "data" not in req_data:
                return web.Response(status=http.HTTPStatus.UNAUTHORIZED)

            message += req_data["data"].encode()
            for file in req_files:
                if file is not None:
                    message += file[1]

            signature = base64.b64decode(req_data["signature"].encode())
            try:
                _check_signature(signature, message)
                json_data = json.loads(req_data["data"])
            except cryptography.exceptions.InvalidSignature:
                return web.Response(status=http.HTTPStatus.FORBIDDEN)
            except json.JSONDecodeError:
                return web.Response(status=http.HTTPStatus.BAD_REQUEST)

            return await handler(request, *args, **kwargs, files=req_files, json_data=json_data)

        return wrapper
    return deco
