from .NinjaKiwiRequests import NinjaKiwiRequests


class NinjaKiwiMock(NinjaKiwiRequests):
    @staticmethod
    async def get_btd6_user(oak: str) -> dict | None:
        if "wrong" in oak:
            return None
        if "correct" in oak:
            return {
                "avatarURL":
                    "https://static-api.nkstatic.com/appdocs/4/assets/opendata/a5d32db006cb5d8d535a14494320fc92_ProfileAvatar26.png",
                "bannerURL":
                    "https://static-api.nkstatic.com/appdocs/4/assets/opendata/aaeaf38ca1c20d6df888cae9c3c99abe_ProfileBanner43.png",
            }
        return await super().get_btd6_user(oak)

    @staticmethod
    async def get_btd6_user_save(oak: str) -> dict | None:
        if "wrong" in oak:
            return None
        if "correct" in oak:
            return {}
        return await super().get_btd6_user_save(oak)
