import asyncio
import src.db.connection
from src.db.models import User, PartialUser, MaplistProfile, PartialMap, ListCompletion
from src.utils.misc import list_eq
postgres = src.db.connection.postgres


@postgres
async def get_user_min(id: str, conn=None) -> PartialUser | None:
    """id can be either the Discord ID or the name"""
    if id.isnumeric():
        payload = await conn.fetch("""
            SELECT discord_id, name, nk_oak
            FROM users
            WHERE discord_id=$1
            UNION
            SELECT discord_id, name, nk_oak
            FROM users
            WHERE name=LOWER($2)
        """, int(id), id)
    else:
        payload = await conn.fetch("""
            SELECT discord_id, name, nk_oak
            FROM users
            WHERE name=LOWER($1)
        """, id)
    if not len(payload):
        return None

    pl_user = payload[0]
    return PartialUser(
        int(pl_user[0]), pl_user[1], pl_user[2]
    )


@postgres
async def get_completions_by(id, idx_start=0, amount=50, conn=None) -> list[ListCompletion]:
    payload = await conn.fetch(
        f"""
        WITH unique_runs AS (
            SELECT DISTINCT map, black_border, no_geraldo, current_lcc
            FROM list_completions
            WHERE user_id=$1
            ORDER BY current_lcc DESC,
                no_geraldo DESC,
                black_border DESC
            LIMIT $3
            OFFSET $2
        )
        SELECT
            lc.map, lc.black_border, lc.no_geraldo, lc.current_lcc,
            m.name, m.placement_curver, m.placement_allver, m.difficulty,
            m.r6_start, m.map_data, lc.format
        FROM unique_runs runs
        JOIN list_completions lc
            ON runs.map = lc.map
            AND runs.black_border = lc.black_border
            AND runs.no_geraldo = lc.no_geraldo
            AND runs.current_lcc = lc.current_lcc
        JOIN maps m
            ON lc.map=m.code
        WHERE lc.user_id=$1
            AND m.deleted_on IS NULL
        ORDER BY
            runs.current_lcc DESC,
            runs.no_geraldo DESC,
            runs.black_border DESC,
            runs.map ASC
        """,
        int(id), idx_start, amount,
    )
    if not len(payload):
        return []

    completions = []
    run = payload[0][:4]
    curmap = payload[0][4:10]
    formats = []
    for i, row in enumerate(payload):
        if list_eq(row[:4], run):
            formats.append(row[10])
        else:
            completions.append(
                ListCompletion(
                    PartialMap(
                        run[0], *curmap, None
                    ),
                    int(id),
                    *run[1:4],
                    formats,
                )
            )
            run = row[:4]
            curmap = row[4:10]
            formats = [row[10]]

    completions.append(
        ListCompletion(
            PartialMap(
                run[0], *curmap, None
            ),
            int(id),
            *run[1:4],
            formats,
        )
    )
    return completions


@postgres
async def get_maplist_placement(id, curver=True, type="points", conn=None) -> tuple[int | None, float]:
    verstr = "cur" if curver else "all"
    lbname = "leaderboard" if type == "points" else "lcclb"
    lb_view = f"list_{verstr}ver_{lbname}"

    payload = await conn.fetch(
        f"""
        SELECT user_id, score, placement
        FROM {lb_view}
        WHERE user_id=$1
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
            AND m.deleted_on IS NULL
        """,
        int(id)
    )
    return [PartialMap(*m, None) for m in payload]


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


@postgres
async def edit_user(id: str, name: str, oak: str | None, conn=None) -> bool:
    rows = await conn.execute(
        f"""
        UPDATE users
        SET name=$2, nk_oak=$3
        WHERE discord_id=$1
        """,
        int(id), name, oak,
    )
    return int(rows.split(" ")[1]) == 1
