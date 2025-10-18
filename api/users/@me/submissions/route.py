
from aiohttp import web
from src.utils import routedecos
from src.db.queries import users as user_queries, submissions as submission_queries
from src.exceptions import ValidationException
import math

@routedecos.bearer_auth
@routedecos.with_discord_profile
@routedecos.register_user
async def get(request: web.Request, discord_profile: dict, **_kwargs) -> web.Response:
    """
    summary: Get user submissions
    description: Get a paginated view of the user's submissions (map or completions).
    tags:
    - Users
    parameters:
    - name: type
      in: query
      schema:
        type: string
        enum: [map, completion]
        default: map
    - name: page
      in: query
      schema:
        type: integer
        default: 1
    - name: status
      in: query
      schema:
        type: string
        enum: [pending, all]
        default: all
    responses:
      "200":
        description: A paginated view of the user's submissions.
        content:
          application/json:
            schema:
              type: object
              properties:
                pages:
                  type: integer
                total:
                  type: integer
                data:
                  type: array
                  items:
                    oneOf:
                    - $ref: "#/components/schemas/MapSubmission"
                    - $ref: "#/components/schemas/ListCompletionWithMeta"
    """
    subm_type = request.query.get("type", "map")
    if subm_type not in ["map", "completion"]:
        raise ValidationException("Invalid type specified.")

    try:
        page = int(request.query.get("page", "1"))
        if page <= 0:
            raise ValidationException("Page must be a positive integer.")
    except ValueError:
        raise ValidationException("Page must be a valid integer.")

    status = request.query.get("status", "all")
    if status not in ["pending", "all"]:
        raise ValidationException("Invalid status specified.\n")

    if subm_type == "map":
        total, submissions = await submission_queries.get_map_submissions_by_user(
            user_id=int(discord_profile["id"]), page=page, status=status
        )
    else:
        total, submissions = await submission_queries.get_completion_submissions_by_user(
            user_id=int(discord_profile["id"]), page=page, status=status
        )

    return web.json_response({
        "pages": math.ceil(total / 50),
        "total": total,
        "data": [s.to_dict() for s in submissions]
    })
