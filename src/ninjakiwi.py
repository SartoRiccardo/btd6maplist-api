import src.http
from datetime import datetime, timedelta


def async_cache(maxsize=256, maxduration=3600*24):
    def deco(wrapped):
        cache = {}

        async def wrapper(*args):
            now = datetime.now()
            args_key = hash(args)
            if args_key not in cache or cache[args_key][0] < now:
                cache[args_key] = (
                    now + timedelta(seconds=maxduration),
                    await wrapped(*args)
                )

                if len(cache) > maxsize:
                    entries = sorted([
                        (key, cache[key][0], cache[key][1]) for key in cache
                    ], key=lambda x: x[1])
                    i = 0
                    while len(cache) > maxsize:
                        del cache[entries[i][0]]
                        i += 1

            return cache[args_key][1]
        return wrapper

    return deco


async def get_btd6_user(oak) -> dict | None:
    url = f"https://data.ninjakiwi.com/btd6/users/{oak}"
    response = await src.http.http.get(url)
    if response.status != 200:
        return None
    body = await response.json()
    if not body["success"]:
        return None
    return body["body"]


@async_cache()
async def get_btd6_user_deco(oak) -> dict | None:
    profile = await get_btd6_user(oak)
    if not profile:
        return None
    return {
        "avatarURL": profile["avatarURL"],
        "bannerURL": profile["bannerURL"],
    }
