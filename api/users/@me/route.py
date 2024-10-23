import re
from aiohttp import web
from src.db.queries.users import edit_user, get_user_min
from src.utils.validators import check_fields
from src.requests import ninja_kiwi_api
import src.utils.routedecos
import string


NAME_MAX_LEN = 100
NAME_CHARS = string.ascii_letters + string.digits + "-_. "


async def put_validate(body: dict) -> dict:
    check_fields_exists = {
        "name": str,
        "oak": str | None,
    }
    errors = check_fields(body, check_fields_exists)
    if len(errors):
        return errors

    if "name" not in body:
        errors["name"] = "Missing"
    elif len(body["name"]) > NAME_MAX_LEN:
        errors["name"] = f"Name must be under {NAME_MAX_LEN} characters"
    elif not re.match("^[" + NAME_CHARS.replace(".", "\\.") + "]+$", body["name"]):
        errors["name"] = f"Allowed characters for name: {NAME_CHARS}"
    elif await get_user_min(body["name"]) is not None:
        errors["name"] = "That name is already taken!"

    if "oak" not in body:
        errors["oak"] = "Missing"
    elif body["oak"] is not None:
        if not body["oak"].startswith("oak_"):
            errors["oak"] = "OAKs must start with 'oak_'"
        # elif len(body["oak"]) != 24:
        #     errors["oak"] = "OAKs must be 24 characters long"
        else:
            nk_response = await ninja_kiwi_api().get_btd6_user_save(body["oak"])
            if nk_response is None:
                errors["oak"] = "This OAK doesn't work"

    return errors


@src.utils.routedecos.bearer_auth
@src.utils.routedecos.with_discord_profile
@src.utils.routedecos.validate_json_body(put_validate)
async def put(
        request: web.Request,
        json_body: dict = None,
        discord_profile: dict = None,
        **_kwargs
):
    """
    ---
    description: Modify a user's data.
    tags:
    - Users
    requestBody:
      required: true
      content:
        application/json:
          schema:
            $ref: "#/components/schemas/ProfilePayload"
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
    oak = json_body["oak"] if json_body["oak"] is not None else None
    await edit_user(
        discord_profile["id"],
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
