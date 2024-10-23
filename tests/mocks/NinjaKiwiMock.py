

class NinjaKiwiMock:
    def __init__(
            self,
            error_on_map: bool = False,
            error_on_user: bool = False
    ):
        self.error_on_map = error_on_map
        self.error_on_user = error_on_user

    async def get_btd6_user(self, _oak: str) -> dict | None:
        if self.error_on_user:
            return None
        return {
            "avatarURL":
                "https://static-api.nkstatic.com/appdocs/4/assets/opendata/a5d32db006cb5d8d535a14494320fc92_ProfileAvatar26.png",
            "bannerURL":
                "https://static-api.nkstatic.com/appdocs/4/assets/opendata/aaeaf38ca1c20d6df888cae9c3c99abe_ProfileBanner43.png",
        }

    async def get_btd6_user_save(self, _oak: str) -> dict | None:
        if self.error_on_user:
            return None
        return {}

    async def get_btd6_user_deco(self, oak: str) -> dict | None:
        profile = await self.get_btd6_user(oak)
        if not profile:
            return None
        return {
            "avatarURL": profile["avatarURL"],
            "bannerURL": profile["bannerURL"],
        }

    async def get_btd6_map(self, code: str) -> dict | None:
        if self.error_on_map:
            return None
        return {
            "name": "Big Balls Bog",
            # "createdAt": 1711859799753,
            # "id": "ZFKTGXC",
            # "creator": "https://data.ninjakiwi.com/btd6/users/9fbd108dddc3f8a14e4a8e4e5821e773c40c4ebeca11d031",
            # "gameVersion": "41.2",
            # "map": "CustomMap",
            "mapURL": "https://data.ninjakiwi.com/btd6/maps/map/ZFKTGXC/preview",
            # "plays": 158,
            # "wins": 2,
            # "restarts": 424,
            # "losses": 2359,
            # "upvotes": 13,
            # "playsUnique": 51,
            # "winsUnique": 2,
            # "lossesUnique": 36
        }

