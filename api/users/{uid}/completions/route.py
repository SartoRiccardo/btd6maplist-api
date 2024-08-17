from aiohttp import web
from src.db.queries.users import get_completions_by


PAGE_ENTRIES = 50


async def get(request: web.Request):
    page = 1
    if "page" in request.query and request.query["page"].isnumeric():
        page = int(request.query["page"])
        if page <= 0:
            page = 1

    completions = await get_completions_by(
        request.match_info["uid"],
        idx_start=(page-1)*PAGE_ENTRIES,
        amount=PAGE_ENTRIES,
    )
    return web.json_response([cmp.to_dict() for cmp in completions])
