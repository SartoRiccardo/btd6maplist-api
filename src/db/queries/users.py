import asyncio
import src.db.connection
from src.db.models import User, PartialUser, MaplistProfile, PartialMap, ListCompletion, LCC
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
async def get_completions_by(id: str, idx_start=0, amount=50, conn=None) -> tuple[list[ListCompletion], int]:
    payload = await conn.fetch(
        f"""
        WITH runs_with_flags AS (
            SELECT r.*, (r.lcc = lccs.id AND lccs.id IS NOT NULL) AS current_lcc
            FROM list_completions r
            JOIN listcomp_players ply
                ON ply.run = r.id
            LEFT JOIN lccs_by_map lccs
                ON lccs.id = r.lcc
            WHERE ply.user_id = $1
                and r.accepted
                AND r.deleted_on IS NULL
        ),
        unique_runs AS (
            SELECT
                rwf.id, rwf.map, rwf.black_border, rwf.no_geraldo, rwf.current_lcc,
                rwf.format,
                
                m.name, m.placement_curver, m.placement_allver, m.difficulty,
                m.r6_start, m.map_data, m.optimal_heros, m.map_preview_url,
                m.id, m.created_on
                
                lccs.id, lccs.proof, lccs.leftover,
                
                ARRAY_AGG(ply.user_id) OVER (PARTITION by rwf.id) AS user_ids
            FROM runs_with_flags rwf
            JOIN listcomp_players ply
                ON ply.run = rwf.id
            LEFT JOIN leastcostchimps lccs
                ON rwf.lcc = lccs.id
            JOIN maps m
                ON m.code = rwf.map
            WHERE m.deleted_on IS NULL
        )
        SELECT COUNT(*) OVER() AS total_count, uq.*
        FROM unique_runs uq
        ORDER BY
            uq.map ASC,
            uq.current_lcc DESC,
            uq.no_geraldo DESC,
            uq.black_border DESC
        LIMIT $3
        OFFSET $2
        """,
        int(id), idx_start, amount,
    )

    run_sidx = 1
    map_sidx = 6 + run_sidx
    lcc_sidx = 10 + map_sidx
    group_sidx = 3 + lcc_sidx

    return [
        ListCompletion(
            run[run_sidx],
            PartialMap(
                run[map_sidx+8],
                run[run_sidx+1],
                run[map_sidx],
                run[map_sidx+1],
                run[map_sidx+2],
                run[map_sidx+3],
                run[map_sidx+4],
                run[map_sidx+5],
                None,
                run[map_sidx+6].split(";"),
                run[map_sidx+7],
                None,
                run[map_sidx+9],
            ),
            run[group_sidx],
            run[run_sidx+2],
            run[run_sidx+3],
            run[run_sidx+4],
            run[run_sidx+5],
            LCC(*run[lcc_sidx:group_sidx]) if run[lcc_sidx] else None,
        )
        for run in payload
    ], payload[0][0] if len(payload) else 0


@postgres
async def get_min_completions_by(id: str, conn=None) -> list[ListCompletion]:
    id = int(id)
    payload = await conn.fetch(
        f"""
        WITH runs_with_flags AS (
            SELECT r.*, (r.lcc = lccs.id AND lccs.id IS NOT NULL) AS current_lcc
            FROM list_completions r
            LEFT JOIN lccs_by_map lccs
                ON lccs.id = r.lcc
                and r.accepted
                AND r.deleted_on IS NULL
        )
        SELECT
            rwf.id, rwf.map, rwf.black_border, rwf.no_geraldo, rwf.current_lcc,
            rwf.format
        FROM runs_with_flags rwf
        JOIN listcomp_players ply
            ON ply.run = rwf.id
        WHERE ply.user_id = $1
        """,
        id
    )

    return [
        ListCompletion(
            run[0],
            run[1],
            [id],
            run[2],
            run[3],
            run[4],
            run[5],
            None,
        )
        for run in payload
    ]


@postgres
async def get_maplist_placement(uid: str, curver=True, type="points", conn=None) -> tuple[int | None, float]:
    verstr = "cur" if curver else "all"
    lbname = "leaderboard" if type == "points" else "lcclb"
    lb_view = f"list_{verstr}ver_{lbname}"

    payload = await conn.fetch(
        f"""
        SELECT user_id, score, placement
        FROM {lb_view}
        WHERE user_id=$1
        """,
        int(uid)
    )
    if not len(payload) or not len(payload[0]):
        return None, 0.0
    return int(payload[0][2]), float(payload[0][1])


@postgres
async def get_maps_created_by(uid: str, conn=None) -> list[PartialMap]:
    payload = await conn.fetch(
        """
        SELECT
            m.code, m.name, m.placement_curver, m.placement_allver, m.difficulty,
            m.r6_start, m.map_data, m.optimal_heros, m.map_preview_url, m.id,
            m.new_version, m.created_on
        FROM maps m JOIN creators c
            ON m.id = c.map
        WHERE c.user_id=$1
            AND m.deleted_on IS NULL
        """,
        int(uid)
    )
    return [
        PartialMap(
            m[9],
            m[0],
            m[1],
            m[2],
            m[3],
            m[4],
            m[5],
            m[6],
            None,
            m[7].split(";"),
            m[8],
            m[10],
            m[11],
        )
        for m in payload
    ]


@postgres
async def get_user(id: str, with_completions: bool = False, conn=None) -> User | None:
    puser = await get_user_min(id, conn=conn)
    if not puser:
        return None

    curpt_pos = await get_maplist_placement(id, conn=conn)
    allpt_pos = await get_maplist_placement(id, curver=False, conn=conn)
    curlcc_pos = await get_maplist_placement(id, type="lcc", conn=conn)
    alllcc_pos = await get_maplist_placement(id, curver=False, type="lcc", conn=conn)
    maps = await get_maps_created_by(id, conn=conn)

    comps = []
    if with_completions:
        comps = await get_min_completions_by(id, conn=conn)

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
        maps,
        comps,
    )


@postgres
async def create_user(uid: str, name: str, if_not_exists=True, conn=None) -> bool:
    rows = await conn.execute(
        f"""
        INSERT INTO users(discord_id, name)
        VALUES ($1, $2)
        {"ON CONFLICT DO NOTHING" if if_not_exists else ""}
        """,
        int(uid), name,
    )
    return int(rows.split(" ")[2]) == 1


@postgres
async def edit_user(uid: str, name: str, oak: str | None, conn=None) -> bool:
    rows = await conn.execute(
        f"""
        UPDATE users
        SET name=$2, nk_oak=$3
        WHERE discord_id=$1
        """,
        int(uid), name, oak,
    )
    return int(rows.split(" ")[1]) == 1


@postgres
async def get_completions_on(user_id: str, code: str, conn=None) -> list[ListCompletion]:
    payload = await conn.fetch(
        """
        WITH runs_with_flags AS (
            SELECT r.*, (r.lcc = lccs.id AND lccs.id IS NOT NULL) AS current_lcc
            FROM list_completions r
            LEFT JOIN lccs_by_map lccs
                ON lccs.id = r.lcc
            JOIN listcomp_players ply
                ON ply.run = r.id
            WHERE r.map = $2
                AND ply.user_id = $1
                and r.accepted
                AND r.deleted_on IS NULL
        )
        SELECT
            r.id, r.map, r.black_border, r.no_geraldo, r.current_lcc, r.format,
            lcc.id, lcc.proof, lcc.leftover,
            ARRAY_AGG(ply.user_id) OVER(PARTITION BY r.id) AS user_ids
        FROM runs_with_flags r
        JOIN listcomp_players ply
            ON ply.run = r.id
        LEFT JOIN leastcostchimps lcc
            ON lcc.id = r.lcc
        """,
        int(user_id), code,
    )

    return [
        ListCompletion(
            row[0],
            row[1],
            row[9],
            row[2],
            row[3],
            row[4],
            row[5],
            LCC(row[6], row[7], row[8]) if row[6] else None
        )
        for row in payload
    ]
