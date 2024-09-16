from config import NK_PREVIEW_PROXY

propositions = {
    "list": ["Top 3", "Top 10", "#11 ~ 20", "#21 ~ 30", "#31 ~ 40", "#41 ~ 50"],
    "experts": ["Casual", "Casual/Medium", "Medium", "Medium/Hard", "Hard", "Hard/True", "True"],
}


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