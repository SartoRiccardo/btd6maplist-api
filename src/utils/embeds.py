import json
import aiohttp
from src.db.queries.completions import add_completion_wh_payload
from src.db.queries.mapsubmissions import add_map_submission_wh
from config import NK_PREVIEW_PROXY
from src.utils.emojis import Emj
import src.http
from config import WEBHOOK_LIST_RUN, WEBHOOK_EXPLIST_RUN, WEBHOOK_LIST_SUBM, WEBHOOK_EXPLIST_SUBM

propositions = {
    "list": ["Top 3", "Top 10", "#11 ~ 20", "#21 ~ 30", "#31 ~ 40", "#41 ~ 50"],
    "experts": ["Casual", "Casual/Medium", "Medium", "Medium/High", "High", "High/True", "True"],
}

formats = {
    1: {"emoji": Emj.curver, "name": "Current"},
    2: {"emoji": Emj.allver, "name": "Current"},
    51: {"emoji": Emj.experts, "name": "Expert List"},
}


PENDING_CLR = 0x1e88e5
LIST_CLR = 0x1e88e5
EXPERTS_CLR = 0x1e88e5
FAIL_CLR = 0xb71c1c
ACCEPT_CLR = 0x43a047


def get_avatar_url(discord_profile: dict) -> str:
    return f"https://cdn.discordapp.com/avatars/{discord_profile['id']}/{discord_profile['avatar']}" \
           if "avatar" in discord_profile else discord_profile["avatar_url"]  # Bot-only


def get_mapsubm_embed(
        data: dict,
        discord_profile: dict,
        btd6_map: dict,
) -> list[dict]:
    embeds = [
        {
            "title": f"{btd6_map['name']} - {data['code']}",
            "url": f"https://join.btd6.com/Map/{data['code']}",
            "author": {
                "name": discord_profile["username"],
                "icon_url": get_avatar_url(discord_profile),
            },
            "fields": [
                {
                    "name": f"Proposed {'List Position' if data['type'] == 'list' else 'Difficulty'}",
                    "value":
                        propositions[data["type"]][data["proposed"]]
                        if data['type'] == 'list' else
                        (propositions[data['type']][data["proposed"]] + " Expert"),
                },
            ],
            "color": LIST_CLR if data["type"] == "list" else EXPERTS_CLR
        },
        {
            "url": f"https://join.btd6.com/Map/{data['code']}",
            "image": {
                "url": NK_PREVIEW_PROXY(data["code"]),
            },
        }
    ]
    if data["notes"]:
        embeds[0]["description"] = data["notes"]
    return embeds


def get_runsubm_embed(
        data: dict,
        discord_profile: dict,
        resource: "src.db.models.PartialMap"
) -> list[dict]:
    embeds = [
        {
            "title": f"{resource.name}",
            #  "url": f"https://join.btd6.com/Map/{resource.code}",  URL to run acceptance
            "author": {
                "name": discord_profile["username"],
                "icon_url": get_avatar_url(discord_profile),
            },
            "fields": [
                {
                    "name": "Format",
                    "value": f"{formats[data['format']]['emoji']} {formats[data['format']]['name']}",
                    "inline": True,
                },
            ],
            "color": PENDING_CLR
        },
    ]
    if data["notes"]:
        embeds[0]["description"] = data["notes"]
    if data["no_geraldo"] or data["current_lcc"] or data["black_border"]:
        embeds[0]["fields"].append({
            "name": "Run Properties",
            "value": (f"* {Emj.black_border} Black Border\n" if data["black_border"] else "") +
                     (f"* {Emj.no_geraldo} No Optimal Hero\n" if data["no_geraldo"] else "") +
                     (f"* {Emj.lcc} Least Cash CHIMPS *(leftover: __${data['leftover']:,}__)*\n" if data[
                         "current_lcc"] else ""),
            "inline": True,
        })
    return embeds


async def send_webhook(run_id: int, hook_url: str, form_data: aiohttp.FormData, payload_json: str) -> None:
    resp = await src.http.http.post(hook_url + "?wait=true", data=form_data)
    if not resp.ok:
        raise Exception(f"Webhook returned with: {resp.status}")
    msg_id = (await resp.json())["id"]
    await add_completion_wh_payload(run_id, f"{msg_id};{payload_json}")


async def update_run_webhook(comp: "src.db.models.ListCompletionWithMeta", fail: bool = False) -> None:
    if comp.subm_wh_payload is None or ";" not in comp.subm_wh_payload:
        return
    msg_id, payload = comp.subm_wh_payload.split(";", 1)
    content = json.loads(payload)
    content["embeds"][0]["color"] = FAIL_CLR if fail else ACCEPT_CLR
    hook_url = WEBHOOK_LIST_RUN if 0 < comp.format <= 50 else WEBHOOK_EXPLIST_RUN
    await src.http.http.patch(hook_url + f"/messages/{msg_id}", json=content)
    await add_completion_wh_payload(comp.id, None)


async def update_map_submission_wh(mapsubm: "src.db.models.MapSubmission", fail: bool = False):
    if mapsubm.wh_data is None:
        return
    hook_url = [WEBHOOK_LIST_SUBM, WEBHOOK_EXPLIST_SUBM][mapsubm.for_list]
    msg_id, wh_data = mapsubm.wh_data.split(";", 1)
    wh_data = json.loads(wh_data)
    wh_data["embeds"][0]["color"] = FAIL_CLR if fail else ACCEPT_CLR
    async with src.http.http.patch(hook_url + f"/messages/{msg_id}", json=wh_data) as resp:
        if resp.ok:
            await add_map_submission_wh(mapsubm.code, None)
