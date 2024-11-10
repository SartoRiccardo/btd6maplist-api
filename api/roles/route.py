from aiohttp import web
from src.db.queries.roles import get_roles


async def get(
        _request: web.Request
) -> web.Response:
    """
    ---
    description: Returns a list of available roles.
    tags:
    - Roles
    responses:
      "200":
        description: Returns an array of `Role`.
        content:
          application/json:
            schema:
              type: array
              items:
                $ref: "#/components/schemas/Role"
    """
    roles = await get_roles()
    return web.json_response([r.to_dict() for r in roles])
