import src.http


async def get_btd6_user(oak) -> dict | None:
    url = f"https://data.ninjakiwi.com/btd6/users/{oak}"
    response = await src.http.http.get(url)
    if response.status != 200:
        return None
    body = await response.json()
    if not body["success"]:
        return None
    return body["body"]


async def get_btd6_user_deco(oak) -> dict | None:
    profile = await get_btd6_user(oak)
    if not profile:
        return None
    return {
        "avatarURL": profile["avatarURL"],
        "bannerURL": profile["bannerURL"],
    }


async def get_btd6_map(code) -> dict | None:
    response = await src.http.http.get(f"https://data.ninjakiwi.com/btd6/maps/map/{code}")
    if response.status != 200:
        return None
    body = await response.json()
    if not body["success"]:
        return None
    return body["body"]

