from aiohttp import web
from src.db.queries.users import get_user, edit_user
from src.ninjakiwi import get_btd6_user_deco
import json
import src.http


async def get(request: web.Request):
    user_data = await get_user(request.match_info["uid"])
    if user_data is None:
        return web.json_response({"error": "No user with that ID found."}, status=404)
    deco = {"avatarURL": None, "bannerURL": None}
    if user_data.oak:
        deco = await get_btd6_user_deco(user_data.oak)
    return web.json_response({
        **user_data.to_dict(),
        **deco,
    })


async def put(request: web.Request):
    data = json.loads(await request.text())

    if "token" not in data:
        return web.Response(status=401)

    errors = {}
    if "name" not in data:
        errors["name"] = "Missing name"

    if "oak" not in data:
        errors["oak"] = "Missing oak"
    elif len(data["oak"]):
        if not data["oak"].startswith("oak_"):
            errors["oak"] = "OAKs must start with 'oak_'"
        elif len(data["oak"]) != 24:
            errors["oak"] = "OAKs must be 24 characters long"

    if len(errors):
        return web.json_response({"errors": errors, "data": {}}, status=400)

    disc_response = await src.http.http.get(
        "https://discord.com/api/v10/users/@me",
        headers={"Authorization": f"Bearer {data['token']}"}
    )
    disc_profile = await disc_response.json()
    if disc_profile["id"] != request.match_info["uid"]:
        return web.Response(status=401)

    oak = data["oak"] if len(data["oak"]) else None

    if oak:
        nk_response = await src.http.http.get(f"https://data.ninjakiwi.com/btd6/save/{data['oak']}")
        if nk_response.status != 200 or not (await nk_response.json())["success"]:
            errors["oak"] = "This OAK doesn't work"
            return web.json_response({"errors": errors, "data": {}}, status=400)

    status = 200
    await edit_user(
        request.match_info["uid"],
        data["name"],
        oak,
    )

    return web.json_response({
        "errors": [],
        "data": {
            "name": data["name"],
            "oak": oak,
        },
    }, status=status)
