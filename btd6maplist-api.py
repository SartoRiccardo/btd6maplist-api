import functools
import os
import re
import ssl
import sys
import asyncio
import aiohttp_swagger
import importlib
from importlib import util
import contextlib
import config
import aiohttp_client_cache
from aiohttp import web
import src.http
import src.log
import src.db.connection
import src.db.models
from src.exceptions import ServerException
from src.utils.colors import green, yellow, blue, red, cyan


# https://docs.aiohttp.org/en/v3.8.5/web_advanced.html#complex-applications
async def init_client_session(_app):
    cache = aiohttp_client_cache.SQLiteBackend(
        cache_name=os.path.join(config.PERSISTENT_DATA_PATH, ".cache", "aiohttp-requests.db"),
        expire_after=0,
        urls_expire_after={
            "data.ninjakiwi.com": 3600*24,
            "discord.com/api/v10/users/@me/guilds": 60*5,
            "discord.com/api/v10/guilds/*/roles": 60*5,
            "discord.com": 60*60,
        },
        allowed_codes=(200, 404, 401),
        include_headers=True,
    )

    async def init_session():
        async with aiohttp_client_cache.CachedSession(cache=cache) as session:
            src.http.set_session(session)
            src.http.set_bot_pubkey(config.BOT_PUBKEY)
            while True:
                await session.delete_expired_responses()
                await asyncio.sleep(3600 * 24 * 5)

    tasks = [
        asyncio.create_task(init_session()),
        asyncio.create_task(src.log.init_log()),
    ]

    yield

    [t.cancel() for t in tasks]
    with contextlib.suppress(asyncio.CancelledError):
        [await t for t in tasks]


def start_db_connection(init_database: bool = True):
    async def start(_app):
        await src.db.connection.start(init_database)
    return start


def get_cors_regex(cors_options):
    cors_regex = {}
    for origin in cors_options:
        origin_re = "^" + origin.replace(".", "\\.").replace("*", ".*") + "$"
        cors_regex[origin] = re.compile(origin_re)
    return cors_regex


def cors_handler(cors_options, methods):
    cors_regex = get_cors_regex(cors_options)

    async def handler(request: web.Request):
        if "Origin" not in request.headers:
            return web.Response(status=400)

        allow = False
        for allowed_origin in cors_regex:
            if re.match(cors_regex[allowed_origin], request.headers["Origin"]):
                allow = True
                break

        if not allow:
            return web.Response(status=400)

        return web.Response(
            status=204,
            headers={
                "Access-Control-Allow-Origin": request.headers["Origin"],
                "Access-Control-Allow-Methods": ",".join(methods),
                "Access-Control-Allow-Headers": "X-Requested-With, Authorization, Content-Type",
                # "Access-Control-Max-Age": "86400",
            }
        )
    return handler


def response_on_exception(handler):
    @functools.wraps(handler)
    async def inner(*args, **kwargs) -> web.Response:
        try:
            return await handler(*args, **kwargs)
        except ServerException as exc:
            return exc.to_response()
    return inner


def cors_route(handler, cors_options):
    cors_regex = get_cors_regex(cors_options)

    @functools.wraps(handler)
    async def inner(request: web.Request) -> web.Response:
        response = await handler(request)
        if "Origin" in request.headers:
            for allowed_origin in cors_regex:
                if re.match(cors_regex[allowed_origin], request.headers["Origin"]):
                    response.headers["Access-Control-Allow-Origin"] = request.headers["Origin"]
                    break
        return response

    return inner


allowed_methods = {
    "get": (web.get, green),
    "post": (web.post, yellow),
    "put": (web.put, blue),
    "patch": (web.patch, cyan),
    "delete": (web.delete, red),
}
route_files = {
    "route.py": "",
    "bot.py": "/bot",
}


def get_routes(cur_path: None | list = None) -> list:
    """Dinamically builds routes wrt the /api folder"""
    if cur_path is None:
        cur_path = []
    bpath = os.path.join("api", *cur_path)
    bmodule = "api"

    routes = []
    for file in os.listdir(bpath):
        path = os.path.join(bpath, file)
        if os.path.isdir(path):
            cur_path.append(file)
            routes += get_routes(cur_path)
            cur_path.pop(-1)
        elif file in route_files:
            suffix = route_files[file]

            # https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly
            spec = importlib.util.spec_from_file_location(bmodule, path)
            route = importlib.util.module_from_spec(spec)
            sys.modules[bmodule] = route
            spec.loader.exec_module(route)

            cors_origins = route.cors_origins if hasattr(route, "cors_origins") else config.CORS_ORIGINS
            api_route = "/" + "/".join(cur_path) + suffix
            methods = []
            for method in allowed_methods:
                if not hasattr(route, method):
                    continue
                routefunc, routecolor = allowed_methods[method]
                api_route_str = api_route
                if api_route_str.endswith("/bot"):
                    api_route_str = api_route_str[:-4] + " 🤖"
                print(f"{routecolor(method.upper())}\t{api_route_str}")
                handler = cors_route(
                    response_on_exception(
                        getattr(route, method),
                    ),
                    cors_origins,
                )
                routes.append(routefunc(api_route, handler))
                methods.append(method.upper())
            if len(methods):
                routes.append(web.options(api_route, cors_handler(cors_origins, methods)))

    return routes


def swagger(app):
    def swagger_gen_docs_without_head(app, *args, **kwargs):
        clone_app = web.Application()
        for route in app.router.routes():
            if route.method == "HEAD":
                continue
            clone_app.router.add_route(route.method, route.resource.canonical, route.handler)
        return aiohttp_swagger.helpers.builders.generate_doc_from_each_end_point(clone_app, *args, **kwargs)
    aiohttp_swagger.generate_doc_from_each_end_point = swagger_gen_docs_without_head

    aiohttp_swagger.setup_swagger(
        app,
        swagger_url="/doc",
        ui_version=3,
        api_version="1.0.0",
        title="BTD6 Maplist API",
        description="API for the BTD6 Maplist community. "
                    "All `GET` methods also support `HEAD` with the same documentation.",
        contact="<a href=\"https://github.com/SartoRiccardo\">@SartoRiccardo on GitHub</a>",
        definitions=src.db.models.swagger_definitions,
    )


async def redirect_to_swagger(r):
    return web.Response(status=301, headers={"Location": "/doc"})


def get_application(
        with_swagger: bool = True,
        init_database: bool = True,
) -> web.Application:
    app = web.Application(
        client_max_size=1024**2 * 5 * 4,  # Up to 4x 5MB images.
    )
    app.add_routes(get_routes())

    if with_swagger:
        swagger(app)
        app.router.add_get("/", redirect_to_swagger)

    app.on_startup.append(start_db_connection(init_database))
    app.cleanup_ctx.append(init_client_session)
    return app


if __name__ == '__main__':
    os.chdir(os.path.abspath(os.path.dirname(__file__)))
    app = get_application()

    ssl_context = None
    if os.path.exists("api.btd6maplist.crt") and os.path.exists("api.btd6maplist.key"):
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain("api.btd6maplist.crt", "api.btd6maplist.key")

    web.run_app(app, host=config.APP_HOST, port=config.APP_PORT, ssl_context=ssl_context)
