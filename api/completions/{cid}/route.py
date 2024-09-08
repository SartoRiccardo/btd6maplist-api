from aiohttp import web
import http
from src.db.queries.completions import get_completion, edit_completion, delete_completion
from src.utils.validators import validate_completion
import src.utils.routedecos
from src.utils.forms import get_submission
from config import MAPLIST_EXPMOD_ID, MAPLIST_LISTMOD_ID


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
        request: web.Request,
        maplist_profile: dict = None,
        resource: "src.db.models.ListCompletion" = None,
        **_kwargs,
) -> web.Response:
    """
    ---
    description: |
      Edit a completion. Must be a Maplist and/or Expert List Moderator,
      depending on the completion's old and new `format`s.
    tags:
    - Completions
    parameters:
    - in: path
      name: cid
      required: true
      schema:
        type: string
      description: The completion's ID.
    requestBody:
      required: true
      content:
        application/json:
          schema:
            $ref: "#/components/schemas/ListCompletion"
    responses:
      "204":
        description: The resource was modified correctly
      "400":
        description: |
          One of the fields is badly formatted.
          `data` will be an empty array in this case.
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
                  example: {}
      "401":
        description: Your token is missing, invalid or you don't have the privileges for this.
      "404":
        description: No completion with that ID was found.
    """
    data = await get_submission(request, maplist_profile, resource)
    if isinstance(data, web.Response):
        return data

    await edit_completion(
        resource.id,
        data["black_border"],
        data["no_geraldo"],
        data["format"],
        data["lcc"],
        [int(uid) for uid in data["user_ids"]],
    )
    return web.Response(status=http.HTTPStatus.NO_CONTENT)


@src.utils.routedecos.bearer_auth
@src.utils.routedecos.validate_resource_exists(get_completion, "cid")
@src.utils.routedecos.with_maplist_profile
async def delete(
        _r: web.Request,
        maplist_profile: dict = None,
        resource: "src.db.models.ListCompletion" = None,
        **_kwargs,
) -> web.Response:
    """
    ---
    description: |
      Soft deletes a completion. Must be a Maplist or Expert List Moderator,
      depending on the completion's `format`.
      Deleted completions and all their data are kept in the database, but ignored.
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
      "204":
        description: The resource was deleted correctly
      "401":
        description: Your token is missing, invalid or you don't have the privileges for this.
      "404":
        description: No map with that ID was found.
    """
    if MAPLIST_LISTMOD_ID not in maplist_profile["roles"] and 1 <= resource.format <= 50:
        return web.json_response(
            {"errors": {"format": "You must be a Maplist Moderator"}},
            status=http.HTTPStatus.UNAUTHORIZED,
        )
    if MAPLIST_EXPMOD_ID not in maplist_profile["roles"] and 51 <= resource.format <= 100:
        return web.json_response(
            {"errors": {"format": "You must be an Expert List Moderator"}},
            status=http.HTTPStatus.UNAUTHORIZED,
        )

    if not resource.deleted_on:
        await delete_completion(resource.id)

    return web.Response(status=http.HTTPStatus.NO_CONTENT)
