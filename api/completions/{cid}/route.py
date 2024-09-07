from aiohttp import web
import http
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
              $ref: "#/components/schemas/ListCompletionWithMeta"
      "404":
        description: No code with that ID was found.
    """
    return web.json_response(resource.to_dict(full=True))


@src.utils.routedecos.bearer_auth
@src.utils.routedecos.validate_resource_exists(get_completion, "cid")
@src.utils.routedecos.with_maplist_profile
async def put(
        _r: web.Request,
        maplist_profile: dict = None,
        resouce: "src.db.models.ListCompletion" = None
) -> web.Response:
    return web.Response(status=http.HTTPStatus.NOT_IMPLEMENTED)


@src.utils.routedecos.bearer_auth
@src.utils.routedecos.validate_resource_exists(get_completion, "cid")
@src.utils.routedecos.with_maplist_profile
async def delete(
        _r: web.Request,
        maplist_profile: dict = None,
        resouce: "src.db.models.ListCompletion" = None
) -> web.Response:
    return web.Response(status=http.HTTPStatus.NOT_IMPLEMENTED)