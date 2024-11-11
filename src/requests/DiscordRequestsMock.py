from .DiscordRequests import DiscordRequests
import http
import re
import aiohttp
import random
import config


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
