import http
import config
import aiohttp


class DiscordPermRoles:
    ADMIN = 0b00001
    MAPLIST_MOD = 0b00010
    EXPLIST_MOD = 0b00100
    BANNED = 0b0100
    NEEDS_RECORDING = 0b10000


class DiscordRequestMock:
    def __init__(
            self,
            perms: int = 0,
            unauthorized: bool = False,
            in_maplist: bool = True,
    ):
        self.perms = perms
        self.unauthorized = unauthorized
        self.in_maplist = in_maplist

    async def get_user_profile(self, *args) -> dict:
        if self.unauthorized:
            raise aiohttp.ClientResponseError(None, (), status=http.HTTPStatus.UNAUTHORIZED)

        return {
            "id": "100000",
            "username": "test.user",
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

    async def get_maplist_profile(self, *args) -> dict:
        if self.unauthorized:
            raise aiohttp.ClientResponseError(None, (), status=http.HTTPStatus.UNAUTHORIZED)
        elif not self.in_maplist:
            raise aiohttp.ClientResponseError(None, (), status=http.HTTPStatus.NOT_FOUND)

        roles = []
        if self.perms & DiscordPermRoles.ADMIN:
            roles.append(config.MAPLIST_ADMIN_IDS[0])
        if self.perms & DiscordPermRoles.MAPLIST_MOD:
            roles.append(config.MAPLIST_LISTMOD_ID)
        if self.perms & DiscordPermRoles.EXPLIST_MOD:
            roles.append(config.MAPLIST_EXPMOD_ID)
        if self.perms & DiscordPermRoles.BANNED:
            roles.append(config.MAPLIST_BANNED_ID)
        if self.perms & DiscordPermRoles.NEEDS_RECORDING:
            roles.append(config.MAPLIST_NEEDSREC_ID)

        return {
            "roles": roles,
            "user": {
                "id": "100000",
                "username": "test.user",
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
