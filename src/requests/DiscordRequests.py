import src.http
import config


class DiscordRequests:
    @staticmethod
    async def get_user_profile(access_token: str) -> dict:
        url = "https://discord.com/api/v10/users/@me"
        headers = {"Authorization": f"Bearer {access_token}"}
        async with src.http.http.get(url, headers=headers, raise_for_status=True) as resp:
            return await resp.json()

    @staticmethod
    async def get_maplist_profile(access_token: str) -> dict:
        url = f"https://discord.com/api/v10/users/@me/guilds/{config.MAPLIST_GUILD_ID}/member"
        headers = {"Authorization": f"Bearer {access_token}"}
        async with src.http.http.get(url, headers=headers, raise_for_status=True) as resp:
            return await resp.json()

