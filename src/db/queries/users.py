import asyncio
import src.db.connection
from src.db.models import User, PartialUser, MaplistProfile, PartialMap, ListCompletion
from src.db.queries.leaderboard import q_lb_format
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
async def get_completions_by(id, conn=None) -> list[ListCompletion]:
    payload = await conn.fetch(
        """
        SELECT
            lc.map, lc.black_border, lc.no_geraldo, lc.current_lcc,
            m.name, m.placement_curver, m.placement_allver, m.difficulty,
            m.r6_start, m.map_data
        FROM list_completions lc JOIN maps m ON lc.map=m.code
        WHERE lc.user_id=$1
        """,
        int(id),
    )
    return [
        ListCompletion(
            PartialMap(
                row[0], *row[4:10]
            ),
            int(id),
            *row[1:4],
        )
        for row in payload
    ]


@postgres
async def get_maplist_placement(id, curver=True, type="points", conn=None) -> tuple[int | None, float]:
    verstr = "cur" if curver else "all"
    lbname = "leaderboard" if type == "points" else "lcclb"
    lb_view = f"list_{verstr}ver_{lbname}"

    payload = await conn.fetch(
        f"""
        {q_lb_format.format(lb_view)}
        WHERE lb1.user_id=$1
        """,
        int(id)
    )
    if not len(payload) or not len(payload[0]):
        return None, 0.0
    return int(payload[0][2]), float(payload[0][1])


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
    puser, curpt_pos, allpt_pos, curlcc_pos, alllcc_pos, maps, completions = await asyncio.gather(
        get_user_min(id),
        get_maplist_placement(id),
        get_maplist_placement(id, curver=False),
        get_maplist_placement(id, type="lcc"),
        get_maplist_placement(id, curver=False, type="lcc"),
        get_maps_created_by(id),
        get_completions_by(id)
    )
    if not puser:
        return None

    return User(
        puser.id,
        puser.name,
        puser.oak,
        MaplistProfile(
            curpt_pos[1],
            curpt_pos[0],
            curlcc_pos[1],
            curlcc_pos[0],
        ),
        MaplistProfile(
            allpt_pos[1],
            allpt_pos[0],
            alllcc_pos[1],
            alllcc_pos[0],
        ),
        completions,
        maps,
    )


@postgres
async def create_user(id, name, if_not_exists=True, conn=None) -> bool:
    rows = await conn.execute(
        f"""
        INSERT INTO users(discord_id, name)
        VALUES ($1, $2)
        {"ON CONFLICT DO NOTHING" if if_not_exists else ""}
        """,
        int(id), name,
    )
    return int(rows.split(" ")[2]) == 1
