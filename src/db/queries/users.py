import asyncio
import src.db.connection
from src.db.models import User, PartialUser, MaplistProfile, PartialMap
postgres = src.db.connection.postgres


@postgres
async def get_user_min(id, conn=None) -> PartialUser | None:
    payload = await conn.fetch("""
        SELECT name, nk_oak
        FROM users
        WHERE discord_id=$1
    """, int(id))
    if not len(payload):
        return None

    pl_user = payload[0]
    return PartialUser(
        int(id), pl_user[0], pl_user[1]
    )


@postgres
async def get_maplist_placement(id, curver=True, conn=None) -> tuple[int | None, float]:
    lb_view = "list_curver_leaderboard" if curver else "list_allver_leaderboard"
    payload = await conn.fetch(
        f"""
        SELECT
            lb1.score,
            (
                SELECT COUNT(*)+1
                FROM (
                    SELECT DISTINCT lb2.score
                    FROM {lb_view} lb2
                    WHERE lb2.score > lb1.score
                ) lb3
            ) AS placement
        FROM {lb_view} lb1
        WHERE lb1.user_id=$1
        """,
        int(id)
    )
    if not len(payload[0]):
        return None, 0.0
    return payload[0][1], float(payload[0][0])


@postgres
async def get_lccs_count_for(id, conn=None) -> int:
    return (await conn.fetch(
        """
        SELECT COUNT(*)
        FROM lcc_players
        WHERE user_id=$1
        """,
        int(id)
    ))[0][0]


@postgres
async def get_maps_created_by(id, conn=None) -> list[PartialMap]:
    payload = await conn.fetch(
        """
        SELECT
            m.code, m.name, m.placement_curver, m.placement_allver, m.difficulty,
            m.r6_start, m.map_data
        FROM maps m JOIN creators c
            ON m.code = c.map
        WHERE c.user_id=$1
        """,
        int(id)
    )
    return [PartialMap(*m) for m in payload]


async def get_user(id) -> User | None:
    puser, cur_pos, all_pos, lcc_count, maps = await asyncio.gather(
        get_user_min(id),
        get_maplist_placement(id),
        get_maplist_placement(id, False),
        get_lccs_count_for(id),
        get_maps_created_by(id),
    )

    return User(
        puser.id,
        puser.name,
        puser.oak,
        MaplistProfile(
            lcc_count,
            cur_pos[1],
            cur_pos[0],
            all_pos[1],
            all_pos[0],
        ),
        maps
    )
