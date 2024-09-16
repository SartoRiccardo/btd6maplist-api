from config import NK_PREVIEW_PROXY
from src.utils.emojis import Emj

propositions = {
    "list": ["Top 3", "Top 10", "#11 ~ 20", "#21 ~ 30", "#31 ~ 40", "#41 ~ 50"],
    "experts": ["Casual", "Casual/Medium", "Medium", "Medium/Hard", "Hard", "Hard/True", "True"],
}

formats = [
    {"emoji": Emj.curver, "name": "Current"},
    {"emoji": Emj.allver, "name": "Current"},
    {"emoji": Emj.experts, "name": "Expert List"},
]


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
                "icon_url": f"https://cdn.discordapp.com/avatars/{discord_profile['id']}/{discord_profile['avatar']}" \
                            if "avatar" in discord_profile else discord_profile["avatar_url"],  # Bot-only
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
            "color": 0x2e7d32 if data["type"] == "list" else 0x7b1fa2
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
                "icon_url": f"https://cdn.discordapp.com/avatars/{discord_profile['id']}/{discord_profile['avatar']}",
            },
            "fields": [
                {
                    "name": "Format",
                    "value": f"{formats[data['format'] - 1]['emoji']} {formats[data['format'] - 1]['name']}",
                    "inline": True,
                },
            ],
            "color": 0x2e7d32 if 0 < data["format"] <= 2 else 0x7b1fa2
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