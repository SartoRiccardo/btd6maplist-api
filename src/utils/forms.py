from aiohttp import web
import aiohttp
import http
from src.utils.validators import validate_completion
from src.utils.files import save_media
from config import MEDIA_BASE_URL, MAPLIST_LISTMOD_ID, MAPLIST_EXPMOD_ID


async def get_submission(
        request: web.Request,
        maplist_profile: dict,
        resource: "src.db.models.ListCompletion" = None,
) -> dict | web.Response:
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

            if resource is not None:
                if MAPLIST_LISTMOD_ID not in maplist_profile["roles"] and \
                        (1 <= resource.format <= 50 or 1 <= data["format"] <= 50):
                    return web.json_response(
                        {"errors": {"format": "You must be a Maplist Moderator"}},
                        status=http.HTTPStatus.UNAUTHORIZED,
                    )
                if MAPLIST_EXPMOD_ID not in maplist_profile["roles"] and \
                        (51 <= resource.format <= 100 or 51 <= data["format"] <= 100):
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

    return data
