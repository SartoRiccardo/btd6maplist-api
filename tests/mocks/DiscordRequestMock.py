import http
import config
import aiohttp
import random
from itertools import chain


class DiscordPermRoles:
    ADMIN = 2 ** 0
    MAPLIST_MOD = 2 ** 1
    EXPLIST_MOD = 2 ** 2
    BANNED = 2 ** 3
    NEEDS_RECORDING = 2 ** 4
    MAPLIST_OWNER = 2 ** 5
    EXPLIST_OWNER = 2 ** 6


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

    async def execute_webhook(self, *args, wait: bool = False) -> str:
        if wait:
            return str(int(self.wh_rand.random() * 1_000_000_000_000))

    @staticmethod
    async def patch_webhook(*args) -> bool:
        return True

    @staticmethod
    async def delete_webhook(*args) -> None:
        pass

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
