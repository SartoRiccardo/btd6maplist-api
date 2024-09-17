import http
import re
from aiohttp import web
from src.db.queries.users import get_user, edit_user, get_user_min
from src.ninjakiwi import get_btd6_user_deco
import src.http
import src.utils.routedecos
import string


NAME_MAX_LEN = 100
NAME_CHARS = string.ascii_letters + string.digits + "-_."


async def get(request: web.Request):
    """
    ---
    description: Returns an user's data.
    tags:
    - Users
    parameters:
    - in: path
      name: uid
      required: true
      schema:
        type: integer
      description: The user's Discord ID.
    responses:
      "200":
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/User"
    """
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


async def put_validate(body: dict) -> dict:
    errors = {}
    if "name" not in body:
        errors["name"] = "Missing name"
    elif len(body["name"]) > NAME_MAX_LEN:
        errors["name"] = f"Name must be under {NAME_MAX_LEN} characters"
    elif not re.match("^[" + NAME_CHARS.replace(".", "\\.") + "]+$", body["name"]):
        errors["name"] = f"Allowed characters for name: {NAME_CHARS}"
    elif await get_user_min(body["name"]):
        errors["name"] = "An user by that name already exists!"

    if "oak" not in body:
        errors["oak"] = "Missing oak"
    elif len(body["oak"]):
        if not body["oak"].startswith("oak_"):
            errors["oak"] = "OAKs must start with 'oak_'"
        # elif len(body["oak"]) != 24:
        #     errors["oak"] = "OAKs must be 24 characters long"
        else:
            nk_response = await src.http.http.get(f"https://data.ninjakiwi.com/btd6/save/{body['oak']}")
            if not nk_response.ok or not (await nk_response.json())["success"]:
                errors["oak"] = "This OAK doesn't work"

    return errors


@src.utils.routedecos.bearer_auth
@src.utils.routedecos.validate_json_body(put_validate)
@src.utils.routedecos.with_discord_profile
async def put(request: web.Request, json_body: dict = None, discord_profile: dict = None, **_kwargs):
    """
    ---
    description: Modify an user's data.
    tags:
    - Users
    parameters:
    - in: path
      name: uid
      required: true
      schema:
        type: integer
      description: The user's Discord ID.
    requestBody:
      required: true
      content:
        application/json:
          schema:
            $ref: "#/components/schemas/Profile"
    responses:
      "200":
        description: |
          Returns the modified user.
          `error` will be an empty object in this case.
        content:
          application/json:
            schema:
              type: object
              properties:
                errors:
                  type: object
                data:
                  $ref: "#/components/schemas/Profile"
      "400":
        description: |
          One of the fields is badly formatted.
          `data` will be an empty object in this case.
        content:
          application/json:
            schema:
              type: object
              properties:
                errors:
                  type: object
                  description: Each key-value pair is the key of the wrong field and a description as to why.
                data:
                  type: object
      "401":
        description: Your token is missing, or invalid.
    """
    if discord_profile["id"] != request.match_info["uid"]:
        return web.Response(status=http.HTTPStatus.UNAUTHORIZED)

    oak = json_body["oak"] if len(json_body["oak"]) else None
    await edit_user(
        request.match_info["uid"],
        json_body["name"],
        oak,
    )
    return web.json_response({
        "errors": [],
        "data": {
            "name": json_body["name"],
            "oak": oak,
        },
    })
