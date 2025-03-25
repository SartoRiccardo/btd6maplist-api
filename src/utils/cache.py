from datetime import datetime, timedelta
from functools import wraps


def cache_for(seconds: int):
    cache = {}

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # TODO also put kwargs in the key but for now I dont need it
            now = datetime.now()
            if args not in cache or cache[args][1] < now:
                cache[args] = (await func(*args, **kwargs), now + timedelta(seconds=seconds))
            return cache[args][0]
        return wrapper

    return decorator
