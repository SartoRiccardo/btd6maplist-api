from .DiscordRequests import DiscordRequests
import http
import re
import aiohttp
import random
import config
from .DiscordModelsMock import RoleMock, MemberMock, GuildMock

P_MANAGE_ROLES = 1 << 28
P_ADMIN = 1 << 3
_roles = [RoleMock(i, f"Role{i}", i) for i in range(15)]
_bot_guilds = _user_guilds = [
    GuildMock(4, "G4", member=MemberMock(), permissions=P_ADMIN),
    GuildMock(5, "G5", member=MemberMock(), permissions=P_ADMIN),
]
for i in range(20):
    guild = _bot_guilds[i % len(_bot_guilds)]
    role = RoleMock(i, f"Role #{i // 2 + 1}", i // 2 + 1)
    guild.roles.append(role)
    guild.member.roles.append(role)


def get_user_id(access_token: str) -> int | None:
    if (match := re.match(r"mock_discord_(\d+)", access_token)) is not None:
        return int(match.group(1))
    return None


class DiscordRequestsMock(DiscordRequests):
    @staticmethod
    async def setup():
        pass

    @staticmethod
    async def get_user_profile(access_token: str) -> dict:
        if user_id := get_user_id(access_token):
            raise aiohttp.ClientResponseError(None, (), status=http.HTTPStatus.UNAUTHORIZED)

        return {
            "id": str(user_id),
            "username": f"User {user_id}",
            "avatar": "31eb929ef84cce316fa9be34fc9b1c5b",
            "global_name": "Test User",
            # "discriminator": "0",
            # "public_flags": 0,
            # "flags": 0,
            # "banner": None,
            # "accent_color": 14400186,
            # "avatar_decoration_data": None,
            # "banner_color": "#dbbaba",
            # "clan": None,
            # "mfa_enabled": True,
            # "locale": "en-US",
            # "premium_type": 0
        }

    @staticmethod
    async def execute_webhook(hook_url: str, data: aiohttp.FormData, wait: bool = False) -> str:
        if wait:
            return str(random.randint(1_000_000_000, 1_000_000_000_000))

    @staticmethod
    async def patch_webhook(hook_url: str, message_id: str, data: dict) -> bool:
        return True

    @staticmethod
    async def delete_webhook(hook_url: str, message_id: str) -> None:
        pass

    @staticmethod
    async def get_user_guilds(self, *args, **kwargs) -> list[dict]:
        return [g.to_dict() for g in _user_guilds]

    @staticmethod
    async def get_application_guilds(*args, **kwargs) -> list[dict]:
        return [g.to_dict() for g in _bot_guilds]

    @staticmethod
    async def get_guild_roles(guild_id: str | int) -> list[dict]:
        if isinstance(guild_id, str):
            guild_id = int(guild_id)
        for guild in _bot_guilds:
            if guild_id == guild.id:
                return [r.to_dict() for r in guild.roles]

    @staticmethod
    async def get_application_guild_member(guild_id: str | int) -> dict | None:
        if isinstance(guild_id, str):
            guild_id = int(guild_id)
        try:
            return next(g for g in _bot_guilds if g.id == guild_id).member.to_dict()
        except StopIteration:
            return None
