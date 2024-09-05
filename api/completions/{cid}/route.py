from aiohttp import web
from src.db.queries.completions import get_completion
import src.utils.routedecos


@src.utils.routedecos.validate_resource_exists(get_completion, "cid")
async def get(_r: web.Request, resource: "src.db.models.ListCompletion" = None):
    """
    ---
    description: Returns a completion's data.
    tags:
    - Completions
    parameters:
    - in: path
      name: cid
      required: true
      schema:
        type: string
      description: The completion's ID.
    responses:
      "200":
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/ListCompletion"
      "404":
        description: No code with that ID was found.
    """
    return web.json_response(resource.to_dict())
