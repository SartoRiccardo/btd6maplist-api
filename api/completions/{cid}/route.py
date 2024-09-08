from aiohttp import web
import aiohttp
import http
from src.db.queries.completions import get_completion, edit_completion
from src.utils.validators import validate_completion
from src.utils.files import save_media
import src.utils.routedecos
from config import MEDIA_BASE_URL, MAPLIST_LISTMOD_ID, MAPLIST_EXPMOD_ID


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
    proof_ext = None
    file_contents = None
    data = None

    reader = await request.multipart()
    while part := await reader.next():
        if part.name == "proof_completion":
            # Max 2MB cause of the Application init
            proof_ext = part.headers[aiohttp.hdrs.CONTENT_TYPE].split("/")[-1]
            file_contents = await part.read(decode=False)

        elif part.name == "data":
            data = await part.json()
            if len(errors := await validate_completion(data)):
                return web.json_response({"errors": errors}, status=http.HTTPStatus.BAD_REQUEST)

            if MAPLIST_LISTMOD_ID not in maplist_profile["roles"] and \
                    (1 <= resource.format <= 2 or 1 <= data["format"] <= 2):
                return web.json_response(
                    {"errors": {"format": "You must be a Maplist Moderator"}},
                    status=http.HTTPStatus.UNAUTHORIZED,
                )
            if MAPLIST_EXPMOD_ID not in maplist_profile["roles"] and \
                    (3 <= resource.format <= 3 or 3 <= data["format"] <= 3):
                return web.json_response(
                    {"errors": {"format": "You must be an Expert List Moderator"}},
                    status=http.HTTPStatus.UNAUTHORIZED,
                )

    if data["lcc"] is not None:
        if file_contents is None and "proof_completion" not in data["lcc"]:
            return web.json_response({
                "errors": {
                    "lcc.proof_url": "Must compile at least one of these two",
                    "lcc.proof_file": "Must compile at least one of these two",
                },
            }, status=http.HTTPStatus.BAD_REQUEST)

        if "proof_completion" not in data["lcc"]:
            proof_fname, fpath = await save_media(file_contents, proof_ext, prefix="proof_")
            data["lcc"]["proof"] = f"{MEDIA_BASE_URL}/{proof_fname}"
        else:
            data["lcc"]["proof"] = data["lcc"]["proof_completion"]

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
        resouce: "src.db.models.ListCompletion" = None,
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

    return web.Response(status=http.HTTPStatus.NOT_IMPLEMENTED)
