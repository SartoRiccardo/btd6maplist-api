import json
import aiohttp
from src.db.queries.completions import add_completion_wh_payload
from src.db.queries.mapsubmissions import set_map_submission_wh, get_map_submissions
from src.db.queries.format import get_format
from config import NK_PREVIEW_PROXY
from src.utils.emojis import Emj
import src.http
from ..requests import discord_api
from src.utils.formats.formatinfo import format_info
from src.exceptions import ValidationException


PENDING_CLR = 0x1e88e5
FAIL_CLR = 0xb71c1c
ACCEPT_CLR = 0x43a047


def get_avatar_url(discord_profile: dict) -> str:
    return f"https://cdn.discordapp.com/avatars/{discord_profile['id']}/{discord_profile['avatar']}" \
           if "avatar" in discord_profile else discord_profile["avatar_url"]  # Bot-only


async def get_mapsubm_embed(
        data: dict,
        discord_profile: dict,
        btd6_map: dict,
) -> list[dict]:
    field_proposed = None
    if data["format"] in format_info:
        if isinstance(format_info[data["format"]].proposed_values, tuple):
            prop_name, prop_labels = format_info[data["format"]].proposed_values
            if not (0 <= data["proposed"] < len(prop_labels)):
                raise ValidationException({"proposed": "Out of range"})
            prop_label = prop_labels[data["proposed"]]
        else:
            prop_name, prop_label = await format_info[data["format"]].proposed_values(data["proposed"])
        field_proposed = {
            "name": f"Proposed {prop_name}",
            "value": prop_label,
        }

    embeds = [
        {
            "title": f"{btd6_map['name']} - {data['code']}",
            "url": f"https://join.btd6.com/Map/{data['code']}",
            "author": {
                "name": discord_profile["username"],
                "icon_url": get_avatar_url(discord_profile),
            },
            "color": PENDING_CLR
        },
        {
            "url": f"https://join.btd6.com/Map/{data['code']}",
            "image": {
                "url": NK_PREVIEW_PROXY(data["code"]),
            },
        }
    ]

    if field_proposed:
        embeds[0]["fields"] = [field_proposed]

    if data["notes"]:
        embeds[0]["description"] = data["notes"]
    return embeds


async def get_runsubm_embed(
        data: dict,
        discord_profile: dict,
        resource: "src.db.models.PartialMap"
) -> list[dict]:
    format = await get_format(data["format"])
    embeds = [
        {
            "title": f"{resource.name}",
            "author": {
                "name": discord_profile["username"],
                "icon_url": get_avatar_url(discord_profile),
            },
            "fields": [
                {
                    "name": "Format",
                    "value": f"{format.emoji} {format.name}",
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
    if len(data["video_proof_url"]):
        embeds[0]["fields"].append({
            "name": "Video Proof URL" + ("" if len(data["video_proof_url"]) == 1 else "s"),
            "value": data['video_proof_url'][0]
                if len(data["video_proof_url"]) == 1 else
                ("- " + "\n- ".join(data["video_proof_url"])),
            "inline": False,
        })
    return embeds


async def send_run_webhook(run_id: int, format_id: int, form_data: aiohttp.FormData, payload_json: str) -> None:
    list_format = await get_format(format_id)
    hook_url = list_format.run_submission_wh if list_format else None
    if hook_url is None:
        return

    msg_id = await discord_api().execute_webhook(hook_url, form_data, wait=True)
    await add_completion_wh_payload(run_id, f"{msg_id};{payload_json}")


async def update_run_webhook(comp: "src.db.models.ListCompletionWithMeta", fail: bool = False) -> None:
    if comp.subm_wh_payload is None or ";" not in comp.subm_wh_payload:
        return
    msg_id, payload = comp.subm_wh_payload.split(";", 1)
    content = json.loads(payload)
    content["embeds"][0]["color"] = FAIL_CLR if fail else ACCEPT_CLR

    list_format = await get_format(comp.format)
    hook_url = list_format.run_submission_wh if list_format else None
    if hook_url is None:
        return

    if await discord_api().patch_webhook(hook_url, msg_id, content):
        await add_completion_wh_payload(comp.id, None)


async def update_map_submission_wh(mapsubm: "src.db.models.MapSubmission", fail: bool = False):
    if mapsubm.wh_msg_id is None:
        return

    list_format = await get_format(mapsubm.format_id)
    hook_url = list_format.map_submission_wh if list_format else None
    if hook_url is None:
        return

    wh_data = json.loads(mapsubm.wh_data)
    wh_data["embeds"][0]["color"] = FAIL_CLR if fail else ACCEPT_CLR
    if await discord_api().patch_webhook(hook_url, mapsubm.wh_msg_id, wh_data):
        await set_map_submission_wh(mapsubm.id, None, None)


async def send_map_submission_wh(
        prev_submission: "src.db.models.MapSubmission",
        format_id: int,
        submission_id: int,
        wh_data: dict,
) -> None:
    if prev_submission and prev_submission.wh_msg_id:
        old_list_format = await get_format(prev_submission.format_id)
        old_hook_url = old_list_format.map_submission_wh if old_list_format else None
        await discord_api().delete_webhook(old_hook_url, prev_submission.wh_msg_id)

    list_format = await get_format(format_id)
    hook_url = list_format.map_submission_wh if list_format else None
    if hook_url is None:
        return

    form_data = aiohttp.FormData()
    wh_data_str = json.dumps(wh_data)
    form_data.add_field("payload_json", wh_data_str)

    msg_id = await discord_api().execute_webhook(hook_url, form_data, wait=True)
    await set_map_submission_wh(submission_id, msg_id, wh_data_str)


async def map_change_update_map_submission_wh(map_code: str, map_data: dict) -> None:
    new_formats = [
        format_id
        for format_id in format_info
        if map_data.get(format_info[format_id].key) is not None
    ]

    _, submissions = await get_map_submissions(on_code=map_code, on_formats=new_formats)
    for subm in submissions:
        if subm is None or subm.wh_msg_id is None:
            return

        list_format = await get_format(subm.wh_msg_id)
        hook_url = list_format.map_submission_wh if list_format else None
        if hook_url is None:
            return

        wh_data = json.loads(subm.wh_data)
        wh_data["embeds"][0]["color"] = ACCEPT_CLR
        async with src.http.http.patch(hook_url + f"/messages/{subm.wh_msg_id}", json=wh_data) as resp:
            if resp.ok:
                await set_map_submission_wh(subm.id, None, None)
