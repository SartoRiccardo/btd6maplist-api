import aiohttp_client_cache

http: aiohttp_client_cache.CachedSession


def set_session(pool: aiohttp_client_cache.CachedSession) -> None:
    global http
    http = pool
