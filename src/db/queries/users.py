import asyncio
import src.db.connection
from src.utils.misc import list_rm_dupe
from src.db.models import User, PartialUser, MaplistProfile, PartialMap, ListCompletion, LCC, MaplistMedals
postgres = src.db.connection.postgres


@postgres
async def get_user_min(id: str, conn=None) -> PartialUser | None:
    """id can be either the Discord ID or the name"""
    if id.isnumeric():
        payload = await conn.fetch("""
            SELECT discord_id, name, nk_oak, has_seen_popup
            FROM users
            WHERE discord_id=$1
            UNION
            SELECT discord_id, name, nk_oak, has_seen_popup
            FROM users
            WHERE LOWER(name)=LOWER($2)
        """, int(id), id)
    else:
        payload = await conn.fetch("""
            SELECT discord_id, name, nk_oak, has_seen_popup
            FROM users
            WHERE LOWER(name)=LOWER($1)
        """, id)
    if not len(payload):
        return None

    pl_user = payload[0]
    return PartialUser(
        int(pl_user[0]), pl_user[1], pl_user[2], pl_user[3]
    )


@postgres
async def get_completions_by(
        uid: str,
        formats: list[int],
        idx_start=0,
        amount=50,
        conn=None
) -> tuple[list[ListCompletion], int]:
    extra_args = []
    if len(formats):
        extra_args.append(formats)
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
                {'AND r.format = ANY($4::int[])' if len(formats) > 0 else ''}
                AND r.accepted_by IS NOT NULL
                AND r.deleted_on IS NULL
        ),
        unique_runs AS (
            SELECT DISTINCT ON (rwf.id)
                rwf.id AS run_id, rwf.map, rwf.black_border, rwf.no_geraldo, rwf.current_lcc,
                rwf.format,
                ARRAY_AGG(cp.proof_url) FILTER(WHERE cp.proof_type = 0) OVER(PARTITION BY rwf.id) AS subm_proof_img,
                ARRAY_AGG(cp.proof_url) FILTER(WHERE cp.proof_type = 1) OVER(PARTITION BY rwf.id) AS subm_proof_vid,
                rwf.subm_notes,
                
                m.name, m.placement_curver, m.placement_allver, m.difficulty,
                m.r6_start, m.map_data, m.optimal_heros, m.map_preview_url,
                m.id AS map_id, m.created_on,
                
                lccs.id AS lcc_id, lccs.leftover,
                
                ARRAY_AGG(ply.user_id) OVER (PARTITION by rwf.id) AS user_ids
            FROM runs_with_flags rwf
            JOIN listcomp_players ply
                ON ply.run = rwf.id
            LEFT JOIN completion_proofs cp
                ON cp.run = rwf.id
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
            uq.black_border DESC,
            uq.no_geraldo DESC,
            uq.current_lcc DESC
        LIMIT $3
        OFFSET $2
        """,
        int(uid), idx_start, amount, *extra_args,
    )

    return [
        ListCompletion(
            row["run_id"],
            PartialMap(
                row["map_id"],
                row["map"],
                row["name"],
                row["placement_curver"],
                row["placement_allver"],
                row["difficulty"],
                row["r6_start"],
                row["map_data"],
                None,
                row["optimal_heros"].split(";"),
                row["map_preview_url"],
                None,
                row["created_on"],
            ),
            list_rm_dupe(row["user_ids"], preserve_order=False),
            row["black_border"],
            row["no_geraldo"],
            row["current_lcc"],
            row["format"],
            LCC(row["lcc_id"], row["leftover"]) if row["lcc_id"] else None,
            list_rm_dupe(row["subm_proof_img"]),
            list_rm_dupe(row["subm_proof_vid"]),
            row["subm_notes"],
        )
        for row in payload
    ], payload[0][0] if len(payload) else 0


@postgres
async def get_min_completions_by(uid: str | int, conn=None) -> list[ListCompletion]:
    if isinstance(uid, str):
        uid = int(uid)
    payload = await conn.fetch(
        f"""
        WITH runs_with_flags AS (
            SELECT r.*, (r.lcc = lccs.id AND lccs.id IS NOT NULL) AS current_lcc
            FROM list_completions r
            LEFT JOIN lccs_by_map lccs
                ON lccs.id = r.lcc
                AND r.accepted_by IS NOT NULL
                AND r.deleted_on IS NULL
        )
        SELECT
            rwf.id AS run_id, rwf.map, rwf.black_border, rwf.no_geraldo, rwf.current_lcc, rwf.format
        FROM runs_with_flags rwf
        JOIN listcomp_players ply
            ON ply.run = rwf.id
        WHERE ply.user_id = $1
        """,
        uid
    )

    return [
        ListCompletion(
            run["run_id"],
            run["map"],
            [uid],
            run["black_border"],
            run["no_geraldo"],
            run["current_lcc"],
            run["format"],
            None,
            [],
            [],
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
async def get_user_medals(uid: str, conn=None) -> MaplistMedals:
    payload = await conn.fetch(
        """
        WITH runs_with_flags AS (
            SELECT r.*, (r.lcc = lccs.id AND lccs.id IS NOT NULL) AS current_lcc
            FROM list_completions r
            LEFT JOIN lccs_by_map lccs
                ON lccs.id = r.lcc
        ),
        medals_per_map AS (
            SELECT
                rwf.map,
                BOOL_OR(rwf.black_border) AS black_border,
                BOOL_OR(rwf.no_geraldo) AS no_geraldo,
                BOOL_OR(rwf.current_lcc) AS current_lcc
            FROM runs_with_flags rwf
            JOIN listcomp_players ply
                ON ply.run = rwf.id
            WHERE ply.user_id = $1
                AND rwf.accepted_by IS NOT NULL
                AND rwf.deleted_on IS NULL
            GROUP BY rwf.map
        )
        SELECT
            COUNT(*) AS wins,
            COUNT(CASE WHEN black_border THEN 1 END) AS black_border,
            COUNT(CASE WHEN no_geraldo THEN 1 END) AS no_geraldo,
            COUNT(CASE WHEN current_lcc THEN 1 END) AS current_lcc
        FROM medals_per_map
        """,
        int(uid)
    )

    return MaplistMedals(
        payload[0][0],
        payload[0][1],
        payload[0][2],
        payload[0][3],
    )


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
    medals = await get_user_medals(id, conn=conn)

    comps = []
    if with_completions:
        comps = await get_min_completions_by(id, conn=conn)

    return User(
        puser.id,
        puser.name,
        puser.oak,
        puser.has_seen_popup,
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
        medals,
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
async def edit_user(uid: str, name: str | None, oak: str | None, conn=None) -> bool:
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
async def get_completions_on(
        user_id: str,
        code: str,
        allowed_formats: list[str] = None,
        conn=None
) -> list[ListCompletion]:
    if allowed_formats is None:
        allowed_formats = [1, 51]
    extra_args = []
    if len(allowed_formats):
        extra_args.append(allowed_formats)

    payload = await conn.fetch(
        f"""
        WITH runs_with_flags AS (
            SELECT r.*, (r.lcc = lccs.id AND lccs.id IS NOT NULL) AS current_lcc
            FROM list_completions r
            LEFT JOIN lccs_by_map lccs
                ON lccs.id = r.lcc
            JOIN listcomp_players ply
                ON ply.run = r.id
            WHERE r.map = $2
                {'AND r.format = ANY($3::int[])' if len(allowed_formats) > 0 else ''}
                AND ply.user_id = $1
                AND r.accepted_by IS NOT NULL
                AND r.deleted_on IS NULL
        )
        SELECT DISTINCT ON (run_id)
            r.id AS run_id, r.map, r.black_border, r.no_geraldo, r.current_lcc, r.format,
            lcc.id AS lcc_id, lcc.leftover,
            ARRAY_AGG(ply.user_id) OVER(PARTITION BY r.id) AS user_ids,
            ARRAY_AGG(cp.proof_url) FILTER(WHERE cp.proof_type = 0) OVER(PARTITION BY r.id) AS subm_proof_img,
            ARRAY_AGG(cp.proof_url) FILTER(WHERE cp.proof_type = 1) OVER(PARTITION BY r.id) AS subm_proof_vid,
            r.subm_notes
        FROM runs_with_flags r
        JOIN listcomp_players ply
            ON ply.run = r.id
        LEFT JOIN completion_proofs cp
            ON cp.run = r.id 
        LEFT JOIN leastcostchimps lcc
            ON lcc.id = r.lcc
        """,
        int(user_id), code, *extra_args,
    )

    return [
        ListCompletion(
            row["run_id"],
            row["map"],
            list_rm_dupe(row["user_ids"], preserve_order=False),
            row["black_border"],
            row["no_geraldo"],
            row["current_lcc"],
            row["format"],
            LCC(row["lcc_id"], row["leftover"]) if row["lcc_id"] else None,
            list_rm_dupe(row["subm_proof_img"]),
            list_rm_dupe(row["subm_proof_vid"]),
            row["subm_notes"],
        )
        for row in payload
    ]


@postgres
async def read_rules(uid: int, conn=None) -> None:
    await conn.execute(
        """
        UPDATE users
        SET has_seen_popup=TRUE
        WHERE discord_id=$1
        """,
        uid
    )
