from aiohttp import web
from src.db.queries.maps import get_list_maps


async def get(request: web.Request):
    """
    ---
    description: Returns a list of maps in The List.
    tags:
    - The List
    parameters:
    - in: query
      name: version
      required: false
      schema:
        type: string
        enum: [current, all]
      description: The version of the list to get. Defaults to `current`.
    responses:
      "200":
        description: Returns an array of `PartialListMap`.
        content:
          application/json:
            schema:
              type: array
              items:
                $ref: "#/components/schemas/PartialListMap"
      "400":
        description: Invalid request, the error will be specified in the `error` key.
    """
    current_version = True
    if "version" in request.query:
        version = request.query["version"].lower()
        if version.lower() == "all":
            current_version = False
        elif version != "current":
            return web.json_response(
                {
                    "error": 'Allowed values for "ver": ["current", "all"]'
                },
                status=400,
            )

    maps = await get_list_maps(curver=current_version)
    return web.json_response([m.to_dict() for m in maps])
