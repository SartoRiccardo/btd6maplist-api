import os
import sys
import asyncio
import aiohttp
import importlib
from importlib import util
import contextlib
from config import APP_HOST, APP_PORT
from aiohttp import web
import src.http
import src.db.connection
from src.utils.colors import purple, green, yellow, blue, red


# https://docs.aiohttp.org/en/v3.8.5/web_advanced.html#complex-applications
async def init_client_session(_app):
    async def init_session():
        async with aiohttp.ClientSession() as session:
            src.http.set_session(session)
            await asyncio.Future()  # Run forever

    task = asyncio.create_task(init_session())

    yield

    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task


async def start_db_connection(_app):
    await src.db.connection.start()


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
        elif file == "route.py":
            # https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly
            spec = importlib.util.spec_from_file_location(bmodule, path)
            route = importlib.util.module_from_spec(spec)
            sys.modules[bmodule] = route
            spec.loader.exec_module(route)

            api_route = "/" + "/".join(cur_path)
            if hasattr(route, "get"):
                print(f"+{green('GET')} {api_route}")
                routes.append(web.get(api_route, route.get))
                routes.append(web.get(api_route+"/", route.get))
            if hasattr(route, "post"):
                print(f"+{yellow('POST')} {api_route}")
                routes.append(web.post(api_route, route.post))
                routes.append(web.post(api_route+"/", route.post))
            if hasattr(route, "put"):
                print(f"+{blue('PUT')} {api_route}")
                routes.append(web.put(api_route, route.put))
                routes.append(web.put(api_route+"/", route.put))
            if hasattr(route, "delete"):
                print(f"+{red('DELETE')} {api_route}")
                routes.append(web.delete(api_route, route.delete))
                routes.append(web.delete(api_route+"/", route.delete))

            pass  # Open and append
    return routes


if __name__ == '__main__':
    os.chdir(os.path.abspath(os.path.dirname(__file__)))
    app = web.Application()
    app.add_routes(get_routes())
    app.on_startup.append(start_db_connection)
    app.cleanup_ctx.append(init_client_session)

    print(f"{purple('[START]')} Listening on port {APP_PORT}...")
    web.run_app(app, host=APP_HOST, port=APP_PORT)
