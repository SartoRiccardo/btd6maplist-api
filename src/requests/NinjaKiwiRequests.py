import src.http


class NinjaKiwiRequests:
    @staticmethod
    async def get_btd6_user(oak: str) -> dict | None:
        async with src.http.http.get(f"https://data.ninjakiwi.com/btd6/users/{oak}") as resp:
            if resp.status != 200:
                return None
            body = await resp.json()
            if not body["success"]:
                return None
            return body["body"]

    @staticmethod
    async def get_btd6_user_save(oak: str) -> dict | None:
        async with src.http.http.get(f"https://data.ninjakiwi.com/btd6/save/{oak}") as resp:
            if resp.status != 200:
                return None
            body = await resp.json()
            if not body["success"]:
                return None
            return body["body"]

    @staticmethod
    async def get_btd6_user_deco(oak: str) -> dict | None:
        profile = await NinjaKiwiRequests.get_btd6_user(oak)
        if not profile:
            return None
        return {
            "avatarURL": profile["avatarURL"],
            "bannerURL": profile["bannerURL"],
        }

    @staticmethod
    async def get_btd6_map(code: str) -> dict | None:
        async with src.http.http.get(f"https://data.ninjakiwi.com/btd6/maps/map/{code}") as resp:
            if resp.status != 200:
                return None
            body = await resp.json()
            if not body["success"]:
                return None
            return body["body"]

