import aiohttp

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
        async with src.http.http.post(hook_url, json=data) as resp:
            return resp.ok

    @staticmethod
    async def delete_webhook(hook_url: str, message_id: str) -> None:
        async with src.http.http.delete(f"{hook_url}/messages/{message_id}"):
            pass
