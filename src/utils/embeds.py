from config import NK_PREVIEW_PROXY
from src.utils.emojis import Emj

propositions = {
    "list": ["Top 3", "Top 10", "#11 ~ 20", "#21 ~ 30", "#31 ~ 40", "#41 ~ 50"],
    "experts": ["Casual", "Casual/Medium", "Medium", "Medium/Hard", "Hard", "Hard/True", "True"],
}

formats = {
    1: {"emoji": Emj.curver, "name": "Current"},
    2: {"emoji": Emj.allver, "name": "Current"},
    51: {"emoji": Emj.experts, "name": "Expert List"},
}


LIST_CLR = 0x00897b
EXPERTS_CLR = 0x5e35b1


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
            "color": LIST_CLR if 0 < data["format"] < 50 else EXPERTS_CLR
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