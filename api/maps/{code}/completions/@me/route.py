from aiohttp import web
from src.db.queries.maps import get_map
from src.db.queries.users import get_completions_on
import src.utils.routedecos


@src.utils.routedecos.bearer_auth
@src.utils.routedecos.validate_resource_exists(get_map, "code", partial=True)
@src.utils.routedecos.with_discord_profile
async def get(request: web.Request, discord_profile: dict, **_kw) -> web.Response:
    """
    ---
    description: Returns a list of up to 50 maplist completions of this map.
    tags:
    - Expert List
    - The List
    - Users
    parameters:
    - in: path
      name: code
      required: true
      schema:
        type: string
      description: The map's code.
    responses:
      "200":
        description: Returns an array of `ListCompletion`.
        content:
          application/json:
            schema:
              type: array
              items:
                $ref: "#/components/schemas/ListCompletion"
      "401":
        description: Your token is missing, invalid or you don't have the privileges for this.
      "404":
        description: No map with that ID was found.
    """
    uid = discord_profile["id"]
    code = request.match_info["code"]
    return web.json_response([comp.to_dict() for comp in await get_completions_on(uid, code)])
