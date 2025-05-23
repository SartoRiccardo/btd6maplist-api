import asyncio
from datetime import datetime
import src.db.connection
from src.utils.misc import list_rm_dupe
from src.db.models import (
    User,
    PartialUser,
    MaplistProfile,
    PartialMap,
    ListCompletion,
    LCC,
    MaplistMedals,
    Role,
    AchievementRole,
    DiscordRole,
    Permissions,
    MinimalUser,
)
from src.db.queries.subqueries import leaderboard_name
postgres = src.db.connection.postgres

FormatPlacement = tuple[float, int | None]
UserPlacements = tuple[
    FormatPlacement,
    FormatPlacement,
    FormatPlacement,
    FormatPlacement,
]


@postgres
async def get_user_min(uid: str, conn=None) -> PartialUser | None:
    """id can be either the Discord ID or the name"""
    if uid.isnumeric():
        payload = await conn.fetch("""
            SELECT discord_id, name, nk_oak, has_seen_popup, is_banned
            FROM users
            WHERE discord_id=$1
            
            UNION ALL
            
            SELECT discord_id, name, nk_oak, has_seen_popup, is_banned
            FROM users
            WHERE LOWER(name)=LOWER($2)
        """, int(uid), uid)
    else:
        payload = await conn.fetch("""
            SELECT discord_id, name, nk_oak, has_seen_popup, is_banned
            FROM users
            WHERE LOWER(name)=LOWER($1)
        """, uid)
    if not len(payload):
        return None

    pl_user = payload[0]
    return PartialUser(
        int(pl_user["discord_id"]),
        pl_user["name"],
        pl_user["nk_oak"],
        pl_user["has_seen_popup"],
        pl_user["is_banned"],
    )


@postgres
async def get_completions_by(
        uid: str,
        formats: list[int],
        idx_start: int = 0,
        amount: int = 50,
        timestamp: datetime | None = None,
        conn: "asyncpg.pool.PoolConnectionProxy" = None,
) -> tuple[list[ListCompletion], int]:
    if timestamp is None:
        timestamp = datetime.now()

    extra_args = []
    if len(formats):
        extra_args.append(formats)

    async with conn.transaction():
        # I give up bro this planner cant do planning
        # Makes the thing like 10x faster & shouldn't cause issues
        await conn.execute("SET LOCAL enable_nestloop = off")

        payload = await conn.fetch(
            f"""
            WITH runs_with_flags AS (
                SELECT
                    r.id AS run_meta_id,
                    c.id AS run_id,
                    r.*,
                    c.*,
                    (r.lcc = lccs.id AND lccs.id IS NOT NULL) AS current_lcc
                FROM latest_completions r
                JOIN completions c
                    ON r.completion = c.id
                JOIN comp_players ply
                    ON ply.run = r.id
                LEFT JOIN lccs_by_map lccs
                    ON lccs.id = r.lcc
                WHERE ply.user_id = $1
                    {'AND r.format = ANY($5::int[])' if len(formats) > 0 else ''}
                    AND r.accepted_by IS NOT NULL
                    AND r.deleted_on IS NULL
            ),
            unique_runs AS (
                SELECT DISTINCT ON (rwf.run_id)
                    rwf.run_id, rwf.map, rwf.black_border, rwf.no_geraldo, rwf.current_lcc,
                    rwf.format,
                    ARRAY_AGG(cp.proof_url) FILTER(WHERE cp.proof_type = 0) OVER(PARTITION BY rwf.run_id) AS subm_proof_img,
                    ARRAY_AGG(cp.proof_url) FILTER(WHERE cp.proof_type = 1) OVER(PARTITION BY rwf.run_id) AS subm_proof_vid,
                    rwf.subm_notes,
                    
                    m.name, mlm.placement_curver, mlm.placement_allver, mlm.difficulty,
                    m.r6_start, m.map_data, mlm.optimal_heros, m.map_preview_url, mlm.botb_difficulty,
                    mlm.remake_of,
                    
                    lccs.id AS lcc_id, lccs.leftover,
                    
                    ARRAY_AGG(ply.user_id) OVER (PARTITION by rwf.run_meta_id) AS user_ids
                FROM runs_with_flags rwf
                JOIN comp_players ply
                    ON ply.run = rwf.run_meta_id
                LEFT JOIN completion_proofs cp
                    ON cp.run = rwf.run_id
                LEFT JOIN leastcostchimps lccs
                    ON rwf.lcc = lccs.id
                JOIN latest_maps_meta($4) mlm
                    ON mlm.code = rwf.map
                JOIN maps m
                    ON m.code = mlm.code
                WHERE mlm.deleted_on IS NULL
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
            int(uid), idx_start, amount, timestamp, *extra_args,
        )

    return [
        ListCompletion(
            row["run_id"],
            PartialMap(
                row["map"],
                row["name"],
                row["placement_curver"],
                row["placement_allver"],
                row["difficulty"],
                row["botb_difficulty"],
                row["remake_of"],
                row["r6_start"],
                row["map_data"],
                None,
                row["optimal_heros"].split(";"),
                row["map_preview_url"],
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
            SELECT
                c.id AS run_id,
                r.id AS run_meta_id,
                c.*,
                r.*,
                (r.lcc = lccs.id AND lccs.id IS NOT NULL) AS current_lcc
            FROM latest_completions r
            JOIN completions c
                ON r.completion = c.id
            LEFT JOIN lccs_by_map lccs
                ON lccs.id = r.lcc
            WHERE r.accepted_by IS NOT NULL
                AND r.deleted_on IS NULL
        )
        SELECT
            rwf.map,
            rwf.format,
            BOOL_OR(rwf.black_border) AS black_border,
            BOOL_OR(rwf.no_geraldo) AS no_geraldo,
            BOOL_OR(rwf.current_lcc) AS current_lcc
        FROM runs_with_flags rwf
        JOIN comp_players ply
            ON ply.run = rwf.run_meta_id
        JOIN latest_maps_meta(NOW()::timestamp) m
            ON m.code = rwf.map
        WHERE ply.user_id = $1
            AND m.deleted_on IS NULL
        GROUP BY (rwf.map, rwf.format)
        """,
        uid
    )

    return [
        ListCompletion(
            0,
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
async def get_maps_created_by(
        uid: str,
        timestamp: datetime | None = None,
        conn: "asyncpg.pool.PoolConnectionProxy" = None,
) -> list[PartialMap]:
    if timestamp is None:
        timestamp = datetime.now()

    payload = await conn.fetch(
        """
        SELECT
            m.code, m.name, mlm.placement_curver, mlm.placement_allver, mlm.difficulty,
            m.r6_start, m.map_data, mlm.optimal_heros, m.map_preview_url,
            mlm.botb_difficulty, mlm.remake_of
        FROM maps m
        JOIN latest_maps_meta($2) mlm
            ON m.code = mlm.code
        JOIN creators c
            ON m.code = c.map
        WHERE c.user_id = $1
            AND mlm.deleted_on IS NULL
        """,
        int(uid),
        timestamp,
    )
    return [
        PartialMap(
            pl_map["code"],
            pl_map["name"],
            pl_map["placement_curver"],
            pl_map["placement_allver"],
            pl_map["difficulty"],
            pl_map["botb_difficulty"],
            pl_map["remake_of"],
            pl_map["r6_start"],
            pl_map["map_data"],
            None,
            pl_map["optimal_heros"].split(";"),
            pl_map["map_preview_url"],
        )
        for pl_map in payload
    ]


@postgres
async def get_user_medals(
        uid: str,
        timestamp: datetime | None = None,
        conn: "asyncpg.pool.PoolConnectionProxy" = None,
) -> MaplistMedals:
    if timestamp is None:
        timestamp = datetime.now()

    payload = await conn.fetch(
        """
        WITH runs_with_flags AS (
            SELECT
                r.*,
                (r.lcc = lccs.id AND lccs.id IS NOT NULL) AS current_lcc
            FROM latest_completions r
            LEFT JOIN lccs_by_map lccs
                ON lccs.id = r.lcc
            WHERE r.accepted_by IS NOT NULL
                AND r.deleted_on IS NULL
        ),
        valid_maps AS MATERIALIZED (
            SELECT *
            FROM latest_maps_meta($2::timestamp)
            WHERE deleted_on IS NULL
        ),
        medals_per_map AS (
            SELECT
                c.map,
                BOOL_OR(rwf.black_border) AS black_border,
                BOOL_OR(rwf.no_geraldo) AS no_geraldo,
                BOOL_OR(rwf.current_lcc) AS current_lcc
            FROM runs_with_flags rwf
            JOIN completions c
                ON c.id = rwf.completion
            JOIN comp_players ply
                ON ply.run = rwf.id
            JOIN valid_maps m
                ON c.map = m.code
            WHERE ply.user_id = $1
            GROUP BY c.map
        )
        SELECT
            COUNT(*) AS wins,
            COUNT(CASE WHEN black_border THEN 1 END) AS black_border,
            COUNT(CASE WHEN no_geraldo THEN 1 END) AS no_geraldo,
            COUNT(CASE WHEN current_lcc THEN 1 END) AS current_lcc
        FROM medals_per_map
        """,
        int(uid),
        timestamp
    )

    return MaplistMedals(
        payload[0][0],
        payload[0][1],
        payload[0][2],
        payload[0][3],
    )


@postgres
async def get_user_placements(
        uid: str | int,
        format_id: int,
        timestamp: datetime = None,
        conn: "asyncpg.pool.PoolConnectionProxy" = None,
) -> MaplistProfile:
    if timestamp is None:
        timestamp = datetime.now()
    if isinstance(uid, str):
        uid = int(uid)

    points_lb = leaderboard_name(format_id, "points")
    points_query = ""
    if points_lb:
        points_query = f"""
        UNION ALL
        SELECT 'points' AS lb_type, user_id, score, placement
        FROM {points_lb}
        """

    rows = await conn.fetch(
        f"""
        SELECT *
        FROM (
            SELECT 'lccs' AS lb_type, user_id, score, placement
            FROM {leaderboard_name(format_id, "lccs")}
            
            UNION ALL 
            SELECT 'no_geraldo' AS lb_type, user_id, score, placement
            FROM {leaderboard_name(format_id, "no_geraldo")}
            
            UNION ALL 
            SELECT 'black_border' AS lb_type, user_id, score, placement
            FROM {leaderboard_name(format_id, "black_border")}
            
            {points_query}
        ) AS all_format_lbs
        WHERE user_id = $1
        """,
        uid
    )

    positions = [
        (0, None),
        (0, None),
        (0, None),
        (0, None),
    ]
    pos_to_index = {
        "points": 0,
        "lccs": 1,
        "no_geraldo": 2,
        "black_border": 3,
    }
    for row in rows:
        positions[pos_to_index[row["lb_type"]]] = (row["score"], row["placement"])

    return MaplistProfile(*[
        x  # Flatten the list pretty much
        for placement in positions
        for x in placement
    ])


@postgres
async def get_minimal_profile(
        uid: str | int,
        conn: "asyncpg.pool.PoolConnectionProxy" = None
) -> MinimalUser:
    puser = await get_user_min(uid, conn=conn)
    if not puser:
        return None

    return MinimalUser(
        puser.id,
        puser.name,
        puser.oak,
        puser.has_seen_popup,
        puser.is_banned,
        await get_user_perms(uid, conn=conn),
        await get_user_roles(uid, conn=conn),
        await get_min_completions_by(uid, conn=conn),
    )


@postgres
async def get_user(
        id: str,
        with_completions: bool = False,
        timestamp: datetime | None = None,
        minimal: bool = False,
        conn: "asyncpg.pool.PoolConnectionProxy" = None,
) -> PartialUser | None:
    if timestamp is None:
        timestamp = datetime.now()

    puser = await get_user_min(id, conn=conn)
    if not puser:
        return None
    if minimal:
        return puser

    comps = []
    if with_completions:
        comps = await get_min_completions_by(id, conn=conn)

    return User(
        puser.id,
        puser.name,
        puser.oak,
        puser.has_seen_popup,
        puser.is_banned,
        {
            format_id: await get_user_placements(id, format_id, conn=conn)
            for format_id in [1, 2, 51]
        },
        await get_maps_created_by(id, timestamp=timestamp, conn=conn),
        comps,
        await get_user_medals(id, conn=conn),
        await get_user_roles(puser.id, conn=conn),
        await get_user_achievement_roles(puser.id, conn=conn),
    )


@postgres
async def create_user(
        uid: str | int,
        name: str,
        if_not_exists: bool = True,
        conn: "asyncpg.pool.PoolConnectionProxy" = None,
) -> bool:
    if isinstance(uid, str):
        uid = int(uid)

    rows = await conn.execute(
        f"""
        INSERT INTO users
            (discord_id, name)
        VALUES
            ($1, $2)
        {"ON CONFLICT DO NOTHING" if if_not_exists else ""}
        """,
        uid, name,
    )
    inserted = int(rows.split(" ")[2]) == 1

    if inserted:
        await conn.execute(
            """
            INSERT INTO user_roles
                (user_id, role_id)
            SELECT
                $1, r.id
            FROM roles r
            WHERE r.assign_on_create
            """,
            uid,
        )

    return inserted


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
            SELECT
                r.id AS run_meta_id,
                c.id AS run_id,
                r.*,
                c.*,
                (r.lcc = lccs.id AND lccs.id IS NOT NULL) AS current_lcc
            FROM latest_completions r
            JOIN completions c
                ON r.completion = c.id
            LEFT JOIN lccs_by_map lccs
                ON lccs.id = r.lcc
            JOIN comp_players ply
                ON ply.run = r.id
            WHERE c.map = $2
                {'AND r.format = ANY($3::int[])' if len(allowed_formats) > 0 else ''}
                AND ply.user_id = $1
                AND r.accepted_by IS NOT NULL
                AND r.deleted_on IS NULL
        )
        SELECT DISTINCT ON (run_id)
            r.run_id, r.map, r.black_border, r.no_geraldo, r.current_lcc, r.format,
            lcc.id AS lcc_id, lcc.leftover,
            ARRAY_AGG(ply.user_id) OVER(PARTITION BY r.run_meta_id) AS user_ids,
            ARRAY_AGG(cp.proof_url) FILTER(WHERE cp.proof_type = 0) OVER(PARTITION BY r.run_id) AS subm_proof_img,
            ARRAY_AGG(cp.proof_url) FILTER(WHERE cp.proof_type = 1) OVER(PARTITION BY r.run_id) AS subm_proof_vid,
            r.subm_notes
        FROM runs_with_flags r
        JOIN comp_players ply
            ON ply.run = r.run_meta_id
        LEFT JOIN completion_proofs cp
            ON cp.run = r.run_id
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


@postgres
async def get_user_roles(uid: str | int, conn=None) -> list[Role]:
    if isinstance(uid, str):
        uid = int(uid)
    payload = await conn.fetch(
        """
        SELECT DISTINCT ON (r.id)
            r.id, r.name,
            ARRAY_AGG(rg.role_can_grant) OVER(PARTITION BY r.id) AS can_grant
        FROM roles r
        LEFT JOIN role_grants rg
            ON r.id = rg.role_required
        JOIN user_roles ur
            ON r.id = ur.role_id
        WHERE ur.user_id = $1
            AND NOT r.internal
        """,
        uid
    )

    return [
        Role(
            row["id"],
            row["name"],
            can_grant=[rl for rl in row["can_grant"] if rl is not None],
        )
        for row in payload
    ]


@postgres
async def get_user_achievement_roles(uid: str | int, conn=None) -> list[AchievementRole]:
    if isinstance(uid, str):
        uid = int(uid)

    payload = await conn.fetch(
        """
        WITH applicable_roles AS (
            SELECT DISTINCT ON (ar.lb_format, ar.lb_type)
                ar.*
            FROM all_leaderboards lb
            JOIN achievement_roles ar
                ON lb.lb_format = ar.lb_format AND lb.lb_type = ar.lb_type
            WHERE lb.user_id = $1
                AND (
                    lb.score >= ar.threshold AND NOT ar.for_first
                    OR
                    lb.placement = 1 AND ar.for_first
                )
            ORDER BY
                ar.lb_format,
                ar.lb_type,
                ar.for_first DESC,
                ar.threshold DESC
        )
        SELECT DISTINCT ON (ar.lb_format, ar.lb_type, ar.threshold)
            ar.lb_format,
            ar.lb_type,
            ar.threshold,
            ar.for_first,
            ar.tooltip_description,
            ar.name,
            ar.clr_border,
            ar.clr_inner,
            ARRAY_AGG((dr.guild_id, dr.role_id))
                OVER (PARTITION by (dr.ar_lb_format, dr.ar_lb_type, dr.ar_threshold)) AS linked_roles
        FROM applicable_roles ar
        LEFT JOIN discord_roles dr
            ON ar.lb_format = dr.ar_lb_format
            AND ar.lb_type = dr.ar_lb_type
            AND ar.threshold = dr.ar_threshold
        """,
        uid
    )

    return [
        AchievementRole(
            row["lb_format"],
            row["lb_type"],
            row["threshold"],
            row["for_first"],
            row["tooltip_description"],
            row["name"],
            row["clr_border"],
            row["clr_inner"],
            [
                DiscordRole(gid, rid)
                for gid, rid in row["linked_roles"]
                if gid is not None and rid is not None
            ],
        )
        for row in payload
    ]


@postgres
async def get_user_perms(
        uid: str | int,
        conn: "asyncpg.pool.PoolConnectionProxy" = None
) -> Permissions:
    if isinstance(uid, str):
        uid = int(uid)

    payload = await conn.fetch(
        """
        SELECT
            rfp.format_id, ARRAY_AGG(rfp.permission) AS permissions
        FROM user_roles ur
        JOIN role_format_permissions rfp
            ON ur.role_id = rfp.role_id
        WHERE ur.user_id = $1
        GROUP BY rfp.format_id
        """,
        uid
    )

    return Permissions({row["format_id"]: list(set(row["permissions"])) for row in payload})


@postgres
async def ban_user(
        uid: str | int,
        conn: "asyncpg.pool.PoolConnectionProxy" = None,
) -> None:
    if isinstance(uid, str):
        uid = int(uid)

    async with conn.transaction():
        await conn.execute(
            """
            UPDATE users
            SET
                name = 'user-' || $1,
                is_banned = TRUE
            WHERE discord_id = $1
            """,
            uid,
        )

        await conn.execute(
            """
            DELETE FROM user_roles ur
            WHERE user_id = $1
            """,
            uid,
        )


@postgres
async def unban_user(
        uid: str | int,
        conn: "asyncpg.pool.PoolConnectionProxy" = None,
) -> None:
    if isinstance(uid, str):
        uid = int(uid)

    async with conn.transaction():
        await conn.execute(
            """
            UPDATE users
            SET
                is_banned = FALSE
            WHERE discord_id = $1
            """,
            uid,
        )

        await conn.execute(
            """
            INSERT INTO user_roles
                (user_id, role_id)
            SELECT
                $1, r.id
            FROM roles r
            WHERE r.assign_on_create
            ON CONFLICT DO NOTHING
            """,
            uid,
        )
