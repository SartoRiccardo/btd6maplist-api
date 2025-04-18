import http
import config
import aiohttp
import random
from itertools import chain


class DiscordPermRoles:
    ADMIN = 1
    TECHNICIAN = 1
    MAPLIST_MOD = 4
    EXPLIST_MOD = 5
    MAPLIST_OWNER = 2
    EXPLIST_OWNER = 3
    REQUIRES_RECORDING = 6


class DiscordRequestMock:
    def __init__(
            self,
            perms: int = 0,
            unauthorized: bool = False,
            in_maplist: bool = True,
            wh_message_seed: int = 0,
            user_id: int = 100000,
            username: str = "test.user",
            bot_guilds: list["tests.mocks.GuildMock"] = None,
            user_guilds: list["tests.mocks.GuildMock"] = None,
    ):
        self.perms = perms
        self.unauthorized = unauthorized
        self.in_maplist = in_maplist
        self.wh_rand = random.Random(wh_message_seed)
        self.user_id = user_id
        self.username = username
        self.bot_guilds = bot_guilds if bot_guilds is not None else []
        self.user_guilds = user_guilds if user_guilds is not None else []

        self.wh_events = []

    async def get_user_profile(self, *args) -> dict:
        if self.unauthorized:
            raise aiohttp.ClientResponseError(None, (), status=http.HTTPStatus.UNAUTHORIZED)

        return {
            "id": str(self.user_id),
            "username": self.username,
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

    async def execute_webhook(self, *args, wait: bool = False) -> str | None:
        wh_id = int(self.wh_rand.random() * 1_000_000_000_000)
        self.wh_events.append({"action": "post", "msg_id": wh_id})
        if wait:
            return str(wh_id)

    async def patch_webhook(self, _hook_url: str, message_id: int, *args) -> bool:
        self.wh_events.append({"action": "patch", "msg_id": message_id})
        return True

    async def delete_webhook(self, _hook_url: str, message_id: int) -> None:
        self.wh_events.append({"action": "delete", "msg_id": message_id})

    async def get_user_guilds(self, *args, **kwargs) -> list[dict]:
        return [g.to_dict() for g in self.user_guilds]

    async def get_application_guilds(self, *args, **kwargs) -> list[dict]:
        return [g.to_dict() for g in self.bot_guilds]

    async def get_guild_roles(self, guild_id: str | int) -> list[dict]:
        if isinstance(guild_id, str):
            guild_id = int(guild_id)
        for guild in self.bot_guilds:
            if guild_id == guild.id:
                return [r.to_dict() for r in guild.roles]

    async def get_application_guild_member(self, guild_id: str | int) -> dict | None:
        if isinstance(guild_id, str):
            guild_id = int(guild_id)
        try:
            return next(g for g in self.bot_guilds if g.id == guild_id).member.to_dict()
        except StopIteration:
            return None
