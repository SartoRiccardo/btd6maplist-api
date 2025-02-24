from .DiscordRequests import DiscordRequests
import http
import re
import aiohttp
import random
import config
from .DiscordModelsMock import RoleMock, MemberMock, GuildMock

P_MANAGE_ROLES = 1 << 28
P_ADMIN = 1 << 3
roles = [RoleMock(i, f"Role{i}", i) for i in range(15)]


def get_token_meta(access_token: str) -> tuple[int, int]:
    if (match := re.match(r"mock_discord_(\d+)_(\d+)", access_token)) is not None:
        return int(match.group(1)), int(match.group(2))
    return 0, 1


class DiscordRequestsMock(DiscordRequests):
    UNAUTHORIZED = 2 ** 0
    NOT_IN_MAPLIST = 2 ** 1
    NEEDS_RECORDING = 2 ** 2
    BANNED = 2 ** 3
    MAPLIST_MOD = 2 ** 4
    EXPLIST_MOD = 2 ** 5
    ADMIN = 2 ** 6
    MAPLIST_OWNER = 2 ** 7
    EXPLIST_OWNER = 2 ** 8

    _bot_guilds = [
        GuildMock(1, "G1", roles=roles, member=MemberMock(roles=roles[8:10])),
        GuildMock(2, "G2", roles=roles, member=MemberMock(roles=roles[8:10])),
        GuildMock(3, "G3", roles=roles, member=MemberMock(roles=roles[8:10]), permissions=P_MANAGE_ROLES),
        GuildMock(4, "G4", roles=roles, member=MemberMock(roles=roles[8:10]), permissions=P_ADMIN),
        GuildMock(5, "G5", roles=roles, member=MemberMock(roles=roles[13:]), permissions=P_ADMIN | P_MANAGE_ROLES),
        GuildMock(7, "G7", roles=roles, member=MemberMock(roles=roles[8:10]), permissions=P_MANAGE_ROLES),
    ]
    _user_guilds = [
        GuildMock(1, "G1", roles=roles, member=MemberMock(roles=roles[8:10])),
        GuildMock(2, "G2", roles=roles, member=MemberMock(roles=roles[8:10]), permissions=P_ADMIN),
        GuildMock(3, "G3", roles=roles, member=MemberMock(roles=roles[8:10])),
        GuildMock(4, "G4", roles=roles, member=MemberMock(roles=roles[13:]), permissions=P_MANAGE_ROLES),
        GuildMock(5, "G5", roles=roles, member=MemberMock(roles=roles[8:10]), permissions=P_ADMIN | P_MANAGE_ROLES),
        GuildMock(6, "G6", roles=roles, member=MemberMock(roles=roles[8:10]), permissions=P_MANAGE_ROLES),
    ]

    @staticmethod
    async def get_user_profile(access_token: str) -> dict:
        user_id, user_flags = get_token_meta(access_token)
        if user_flags & DiscordRequestsMock.UNAUTHORIZED:
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
    async def get_maplist_profile(access_token: str) -> dict:
        user_id, user_flags = get_token_meta(access_token)
        if user_flags & DiscordRequestsMock.UNAUTHORIZED:
            raise aiohttp.ClientResponseError(None, (), status=http.HTTPStatus.UNAUTHORIZED)
        elif user_flags & DiscordRequestsMock.NOT_IN_MAPLIST:
            raise aiohttp.ClientResponseError(None, (), status=http.HTTPStatus.NOT_FOUND)

        roles = []
        if user_flags & DiscordRequestsMock.ADMIN:
            roles.append(config.MAPLIST_ADMIN_IDS[0])
        if user_flags & DiscordRequestsMock.MAPLIST_MOD:
            roles.append(config.MAPLIST_LISTMOD_ID)
        if user_flags & DiscordRequestsMock.EXPLIST_MOD:
            roles.append(config.MAPLIST_EXPMOD_ID)
        if user_flags & DiscordRequestsMock.BANNED:
            roles.append(config.MAPLIST_BANNED_ID)
        if user_flags & DiscordRequestsMock.NEEDS_RECORDING:
            roles.append(config.MAPLIST_NEEDSREC_ID)

        return {
            "roles": roles,
            "user": {
                "id": str(user_id),
                "username": f"User {user_id}",
                "avatar": "31eb929ef84cce316fa9be34fc9b1c5b",
                "global_name": "Test User",
                # "discriminator": '0',
                # "public_flags": 0,
                # "flags": 0,
                # "banner": None,
                # "accent_color": 14400186,
                # "avatar_decoration_data": None,
                # "banner_color": "#dbbaba",
                # "clan": None
            },
            # "avatar": None,
            # "banner": None,
            # "communication_disabled_until": None,
            # "flags": 0,
            # "joined_at": "2023-02-20T19:00:00.000000+00:00",
            # "nick": None,
            # "pending": False,
            # "premium_since": None,
            # "unusual_dm_activity_until": None,
            # "mute": False,
            # "deaf": False,
            # "bio": "",
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
        return [g.to_dict() for g in DiscordRequestsMock._user_guilds]

    @staticmethod
    async def get_application_guilds(*args, **kwargs) -> list[dict]:
        return [g.to_dict() for g in DiscordRequestsMock._bot_guilds]

    @staticmethod
    async def get_guild_roles(guild_id: str | int) -> list[dict]:
        if isinstance(guild_id, str):
            guild_id = int(guild_id)
        for guild in DiscordRequestsMock._bot_guilds:
            if guild_id == guild.id:
                return [r.to_dict() for r in guild.roles]

    @staticmethod
    async def get_application_guild_member(guild_id: str | int) -> dict | None:
        if isinstance(guild_id, str):
            guild_id = int(guild_id)
        try:
            return next(g for g in DiscordRequestsMock._bot_guilds if g.id == guild_id).member.to_dict()
        except StopIteration:
            return None
