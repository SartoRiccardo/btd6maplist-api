import asyncio
from aiohttp import web
from src.requests import discord_api
import src.utils.routedecos
from src.utils.misc import extract
from src.exceptions import MissingPermsException

load_guild_roles_sem = asyncio.Semaphore(4)


def find_overlapping_ids(valid_guilds: list[dict], bot_guilds: list[dict], overlapping_ids: list[dict]):
    """
    Find overlapping guild IDs between valid_guilds and bot_guilds and add them to overlapping_ids.
    Removes elements from valid_guilds as they are processed.
    """
    j = 0

    while valid_guilds and j < len(bot_guilds):
        valid_id = int(valid_guilds[0]["id"])
        bot_id = int(bot_guilds[j]["id"])

        if valid_id == bot_id:
            overlapping_ids.append(valid_guilds[0])
            valid_guilds.pop(0)
            j += 1
        elif valid_id < bot_id:
            valid_guilds.pop(0)
        else:
            j += 1


def filter_valid_guilds(guilds: list[dict]) -> list[dict]:
    return sorted([
        g for g in guilds
        if g["owner"] or int(g["permissions"]) & ((1 << 28) | (1 << 3))
    ], key=lambda g: int(g["id"]))


async def load_guild_roles(guild: dict) -> None:
    async with load_guild_roles_sem:
        guild_roles, bot_guild_member = await asyncio.gather(
            discord_api().get_guild_roles(guild["id"]),
            discord_api().get_application_guild_member(guild["id"])
        )

        bot_role_ids = set(bot_guild_member["roles"])
        highest_role_pos = max(
            (
                role["position"] for role in guild_roles
                if role["id"] in bot_role_ids
            ),
            default=0,
        )

        guild["roles"] = sorted([
            extract(rl, ["id", "name", "position"])
            for rl in guild_roles
            if rl["name"] != "@everyone" and not rl["managed"] and rl["position"] < highest_role_pos
        ], key=lambda rl: rl["position"], reverse=True)


@src.utils.routedecos.bearer_auth
@src.utils.routedecos.with_discord_profile
@src.utils.routedecos.require_perms()
async def get(
        _r: web.Request,
        token: str = None,
        permissions: "src.db.models.Permissions" = None,
        **_kwargs,
) -> web.Response:
    """Utility endpoint that gets valid guilds/roles for role picking sections on the website."""
    if not permissions.has_in_any("edit:achievement_roles"):
        raise MissingPermsException("edit:achievement_roles")

    bot_guilds = []
    valid_guilds = filter_valid_guilds(await discord_api().get_user_guilds(token))
    while len(valid_guilds):
        found_guilds = filter_valid_guilds(
            await discord_api().get_application_guilds(int(valid_guilds[0]["id"]) - 1)
        )
        if not len(found_guilds):
            break
        find_overlapping_ids(valid_guilds, found_guilds, bot_guilds)

    await asyncio.gather(*[load_guild_roles(guild) for guild in bot_guilds])
    return web.json_response([
        extract(g, ["id", "name", "roles"])
        for g in bot_guilds
        if len(g["roles"])
    ])
