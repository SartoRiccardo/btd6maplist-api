import aiohttp
import requests
import src.http
import config


class DiscordRequests:
    bot_id = None

    @staticmethod
    def setup():
        if DiscordRequests.bot_id is None:
            url = "https://discord.com/api/v10/users/@me"
            headers = {"Authorization": f"Bot {config.BOT_TOKEN}", "User-Agent": config.BOT_UA}
            resp = requests.get(url, headers=headers)
            DiscordRequests.bot_id = resp.json()["id"]

    @staticmethod
    async def get_user_profile(access_token: str) -> dict:
        url = "https://discord.com/api/v10/users/@me"
        headers = {"Authorization": f"Bearer {access_token}"}
        async with src.http.http.get(url, headers=headers, raise_for_status=True) as resp:
            return await resp.json()

    @staticmethod
    async def execute_webhook(hook_url: str, data: aiohttp.FormData, wait: bool = False) -> str:
        if wait:
            hook_url = f"{hook_url}?wait=true"
        async with src.http.http.post(hook_url, data=data) as resp:
            if wait:
                return (await resp.json())["id"]

    @staticmethod
    async def patch_webhook(hook_url: str, message_id: str, data: dict) -> bool:
        hook_url = f"{hook_url}/messages/{message_id}"
        async with src.http.http.patch(hook_url, json=data) as resp:
            return resp.ok

    @staticmethod
    async def delete_webhook(hook_url: str, message_id: str) -> None:
        async with src.http.http.delete(f"{hook_url}/messages/{message_id}"):
            pass

    @staticmethod
    async def get_user_guilds(access_token: str) -> list[dict]:
        url = "https://discord.com/api/v10/users/@me/guilds"
        headers = {"Authorization": f"Bearer {access_token}"}
        async with src.http.http.get(url, headers=headers) as resp:
            if not resp.ok:
                return []
            return await resp.json()

    @staticmethod
    async def get_application_guilds(after: int = 0) -> list[dict]:
        url = "https://discord.com/api/v10/users/@me/guilds"
        headers = {"Authorization": f"Bot {config.BOT_TOKEN}", "User-Agent": config.BOT_UA}
        async with src.http.http.get(url + f"?after={after}", headers=headers) as resp:
            if not resp.ok:
                return []
            return await resp.json()

    @staticmethod
    async def get_guild_roles(guild_id: str | int) -> list[dict]:
        url = f"https://discord.com/api/v10/guilds/{guild_id}/roles"
        headers = {"Authorization": f"Bot {config.BOT_TOKEN}", "User-Agent": config.BOT_UA}
        async with src.http.http.get(url, headers=headers) as resp:
            if not resp.ok:
                return []
            return await resp.json()

    @staticmethod
    async def get_application_guild_member(guild_id: str | int) -> dict | None:
        url = f"https://discord.com/api/v10/guilds/{guild_id}/members/{DiscordRequests.bot_id}"
        headers = {"Authorization": f"Bot {config.BOT_TOKEN}", "User-Agent": config.BOT_UA}
        async with src.http.http.get(url, headers=headers) as resp:
            if not resp.ok:
                return None
            return await resp.json()
