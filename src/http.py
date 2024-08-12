import aiohttp

http: aiohttp.ClientSession


def set_session(pool: aiohttp.ClientSession) -> None:
    global http
    http = pool
