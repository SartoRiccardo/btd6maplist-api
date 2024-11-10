import http

from aiohttp import web
import src.utils.routedecos
from src.db.queries.users import get_user_min, get_user_roles
from src.db.queries.roles import add_roles, remove_roles
from src.utils.validators import check_fields


def validate_roles(body: dict) -> dict:
    schema = {
        "roles": [{"id": int, "action": str}],
    }
    return check_fields(body, schema)


@src.utils.routedecos.bearer_auth
@src.utils.routedecos.with_discord_profile
@src.utils.routedecos.validate_json_body(validate_roles)
@src.utils.routedecos.validate_resource_exists(get_user_min, "uid")
async def patch(
        _r: web.Request,
        discord_profile: dict = None,
        json_body: dict = None,
        resource: "src.db.models.PartialUser" = None,
        **_kwargs,
) -> web.Response:
    """
    ---
    description: Modify a user's data.
    tags:
    - Users
    - Roles
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              roles:
                type: array
                items:
                  type: object
                  properties:
                    id:
                      description: The ID of the role
                      type: integer
                    action:
                      description: The action to execute for the role
                      type: string
                      enum: [POST, DELETE]
    responses:
      "204":
        description: The roles were modified correctly
      "400":
        description: One of the fields is badly formatted.
        content:
          application/json:
            schema:
              type: object
              properties:
                errors:
                  type: object
                  description: Each key-value pair is the key of the wrong field and a description as to why.
      "401":
        description: Your token is missing, or invalid.
      "403":
        description: You don't have the permissions to grant certain roles.
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
    """
    granter_roles = await get_user_roles(discord_profile["id"])

    can_grant = []
    for role in granter_roles:
        can_grant += role.can_grant
    can_grant = set(can_grant)

    to_delete = []
    to_grant = []
    no_perms = []
    for i, role in enumerate(json_body["roles"]):
        if role["id"] not in can_grant:
            no_perms.append(i)
            continue
        if role["action"].upper() == "DELETE":
            to_delete.append(role["id"])
        elif role["action"].upper() == "POST":
            to_grant.append(role["id"])

    if len(no_perms):
        return web.json_response(
            {"errors": {f"roles[{i}]": "Cannot grant this role" for i in no_perms}},
            status=http.HTTPStatus.FORBIDDEN,
        )

    await add_roles(resource.id, to_grant)
    await remove_roles(resource.id, to_delete)
    return web.Response(status=http.HTTPStatus.NO_CONTENT)
