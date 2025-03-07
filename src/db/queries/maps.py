import asyncio
import src.db.connection
from src.db.models import (
    PartialListMap,
    PartialExpertMap,
    PartialMap,
    Map,
    LCC,
    ListCompletion,
    PartialUser,
)
from src.db.queries.subqueries import get_int_config
from src.utils.misc import list_rm_dupe
postgres = src.db.connection.postgres


@postgres
async def get_list_maps(conn=None, curver=True) -> list[PartialListMap]:
    placement_vname = "placement_curver" if curver else "placement_allver"
    payload = await conn.fetch(f"""
        WITH config_vars AS (
            SELECT
                ({get_int_config("current_btd6_ver")}) AS current_btd6_ver,
                ({get_int_config("map_count")}) AS map_count
        ),
        verified_current AS (
            SELECT DISTINCT map
            FROM verifications
            CROSS JOIN config_vars
            WHERE version=current_btd6_ver
            GROUP BY map
        )
        SELECT
            name,
            m.code,
            vc.map IS NOT NULL,
            placement_allver,
            placement_curver,
            map_preview_url
        FROM maps m
        JOIN map_list_meta mlm
            ON m.code = mlm.code
        LEFT JOIN verified_current vc
            ON m.code = vc.map
        CROSS JOIN config_vars cvar
        WHERE {placement_vname} BETWEEN 1 AND cvar.map_count
            AND deleted_on IS NULL
            AND new_version IS NULL
        ORDER BY {placement_vname} ASC
    """, )
    return [
        PartialListMap(row[0], row[1], row[3 + int(curver)], row[2], row[5])
        for row in payload
    ]


@postgres
async def get_expert_maps(conn=None) -> list[PartialExpertMap]:
    payload = await conn.fetch(
        f"""
        WITH verified_current AS (
            SELECT DISTINCT map
            FROM verifications
            WHERE version = ({get_int_config("current_btd6_ver")})
            GROUP BY map
        )
        SELECT
            m.name,
            m.code,
            mlm.difficulty,
            m.map_preview_url,
            vc.map IS NOT NULL AS verified
        FROM maps m
        JOIN map_list_meta mlm
            ON mlm.code = m.code
        LEFT JOIN verified_current vc
            ON m.code = vc.map
        WHERE difficulty >= 0
            AND deleted_on IS NULL
            AND new_version IS NULL
        """
    )

    return [
        PartialExpertMap(
            row["name"],
            row["code"],
            row["difficulty"],
            row["map_preview_url"],
            row["verified"],
        )
        for row in payload
    ]


@postgres
async def get_map(code: str, partial: bool = False, conn=None) -> Map | PartialMap | None:
    columns = """
        m.code, m.name, mlm.placement_curver, mlm.placement_allver, mlm.difficulty, m.r6_start,
        m.map_data, mlm.deleted_on, mlm.optimal_heros, m.map_preview_url, mlm.created_on, mlm.botb_difficulty
        """
    placement_union = ""
    if code.isnumeric() and abs(int(code)) < 1000:  # Current version index
        placement_union = f"""
            UNION
            
            SELECT 3 AS ord, {columns}
            FROM maps m
            JOIN map_list_meta mlm
                ON m.code = mlm.code
            WHERE mlm.placement_curver = $1::int
                AND mlm.deleted_on IS NULL
                AND mlm.new_version IS NULL
        """
    elif code.startswith("@") and code[1:].isnumeric():  # All versions idx
        code = code[1:]
        placement_union = f"""
            UNION
            
            SELECT 3 AS ord, {columns}
            FROM maps m
            JOIN map_list_meta mlm
                ON m.code = mlm.code
            WHERE m.placement_allver = $1::int
                AND mlm.deleted_on IS NULL
                AND mlm.new_version IS NULL
        """

    pl_map = await conn.fetchrow(
        f"""
        WITH config_values AS (
            SELECT
                (SELECT value::int FROM config WHERE name='current_btd6_ver') AS current_btd6_ver
        ),
        verified_maps AS (
            SELECT v.map, COUNT(*) > 0 AS is_verified
            FROM verifications v
            CROSS JOIN config_values cv
            WHERE v.version=cv.current_btd6_ver
            GROUP BY v.map
        ),
        possible_map AS (
            SELECT *
            FROM (
                SELECT 1 AS ord, {columns}
                FROM maps m
                JOIN map_list_meta mlm
                    ON m.code = mlm.code
                WHERE m.code = $1
                    AND mlm.deleted_on IS NULL
                    AND mlm.new_version IS NULL
                
                UNION
                
                SELECT 2 AS ord, {columns}
                FROM maps m
                JOIN map_list_meta mlm
                    ON m.code = mlm.code
                WHERE LOWER(m.name) = LOWER($1)
                    AND mlm.deleted_on IS NULL
                    AND mlm.new_version IS NULL
                
                UNION
                
                SELECT 4 AS ord, {columns}
                FROM maps m
                JOIN map_list_meta mlm
                    ON m.code = mlm.code
                JOIN map_aliases a
                    ON m.code = a.map
                WHERE LOWER(a.alias) = LOWER($1)
                    OR LOWER(a.alias) = LOWER($2)
                
                {placement_union}
                
                UNION

                (
                    SELECT 6 AS ord, {columns}
                    FROM maps m
                    JOIN map_list_meta mlm
                        ON m.code = mlm.code
                    WHERE m.code = $1
                        AND mlm.deleted_on IS NOT NULL
                    ORDER BY mlm.created_on DESC
                )
            ) possible
            ORDER BY ord
            LIMIT 1
        )
        SELECT
            m.code, m.name, m.placement_curver, m.placement_allver, m.difficulty,
            m.r6_start, m.map_data, v.is_verified, m.deleted_on,
            m.optimal_heros, m.map_preview_url, m.created_on, m.botb_difficulty
        FROM possible_map m
        LEFT JOIN verified_maps v
            ON v.map = m.code
        """,
        code, code.replace(" ", "_")
    )
    if pl_map is None:
        return None

    map_code = pl_map["code"]
    if partial:
        return PartialMap(
            map_code,
            pl_map["name"],
            pl_map["placement_curver"],
            pl_map["placement_allver"],
            pl_map["difficulty"],
            pl_map["botb_difficulty"],
            pl_map["r6_start"],
            pl_map["map_data"],
            pl_map["deleted_on"],
            pl_map["optimal_heros"].split(";"),
            pl_map["map_preview_url"],
            pl_map["created_on"],
        )

    lccs = await get_lccs_for(map_code, conn=conn)
    pl_codes = await conn.fetch("SELECT code, description FROM additional_codes WHERE belongs_to=$1", map_code)
    pl_creat = await conn.fetch(
        """
        SELECT user_id, role, name
        FROM creators c
        JOIN users u
            ON u.discord_id=c.user_id
        WHERE map=$1
        """,
        map_code,
    )
    pl_verif = await conn.fetch(
        f"""
        WITH config_vars AS (
            SELECT
                {get_int_config("current_btd6_ver")} AS current_btd6_ver
        )
        SELECT user_id, version, name
        FROM verifications v
        CROSS JOIN config_vars cv
        JOIN users u
            ON u.discord_id=v.user_id
        WHERE map=$1
            AND (version=cv.current_btd6_ver OR version IS NULL)
        ORDER BY version ASC NULLS FIRST
        """,
        map_code
    )
    pl_compat = await conn.fetch("SELECT status, version FROM mapver_compatibilities WHERE map=$1", map_code)
    pl_aliases = await conn.fetch("SELECT alias FROM map_aliases WHERE map=$1", map_code)

    return Map(
        map_code,
        pl_map["name"],
        pl_map["placement_curver"],
        pl_map["placement_allver"],
        pl_map["difficulty"],
        pl_map["botb_difficulty"],
        pl_map["r6_start"],
        pl_map["map_data"],
        pl_map["deleted_on"],
        pl_map["optimal_heros"].split(";"),
        pl_map["map_preview_url"],
        pl_map["created_on"],
        [(row["user_id"], row["role"], row["name"]) for row in pl_creat],
        [(row["code"], row["description"]) for row in pl_codes],
        [(uid, ver/10 if ver else None, name) for uid, ver, name in pl_verif],
        pl_map["is_verified"],
        lccs,
        pl_compat,
        [row[0] for row in pl_aliases],
    )


def parse_runs_payload(
        payload,
        full_usr_info: bool = False,
) -> list[ListCompletion]:
    comps = []
    for run in payload:
        usr_list = run["user_ids"]
        if full_usr_info:
            usr_list = [
                PartialUser(run["user_ids"][i], run["user_names"][i], None, False)
                for i in range(len(usr_list))
            ]
        usr_list = list_rm_dupe(usr_list, preserve_order=False)

        comps.append(ListCompletion(
            run["run_id"],
            run["map"],
            usr_list,
            run["black_border"],
            run["no_geraldo"],
            run["current_lcc"],
            run["format"],
            LCC(run["lcc_id"], run["leftover"]) if run["lcc_id"] else None,
            list_rm_dupe(run["subm_proof_img"]),
            list_rm_dupe(run["subm_proof_vid"]),
            None,
        ))
    return comps


@postgres
async def get_lccs_for(map_code: str, conn=None) -> list[ListCompletion]:
    payload = await conn.fetch(
        """
        SELECT DISTINCT ON (run_id)
            cm.completion AS run_id, lbm.map, cm.black_border, cm.no_geraldo, TRUE AS current_lcc, cm.format,
            ARRAY_AGG(cp.proof_url) FILTER(WHERE cp.proof_type = 0) OVER(PARTITION BY cm.completion) AS subm_proof_img,
            ARRAY_AGG(cp.proof_url) FILTER(WHERE cp.proof_type = 1) OVER(PARTITION BY cm.completion) AS subm_proof_vid,

            lccs.id AS lcc_id, lccs.leftover,

            ARRAY_AGG(ply.user_id) OVER (PARTITION by cm.id) AS user_ids,
            ARRAY_AGG(u.name) OVER (PARTITION by cm.id) AS user_names
        FROM completions_meta cm
        JOIN lccs_by_map lbm
            ON lbm.id = cm.lcc
        JOIN leastcostchimps lccs
            ON cm.lcc = lccs.id
        JOIN comp_players ply
            ON ply.run = cm.id
        JOIN users u
            ON ply.user_id = u.discord_id
        LEFT JOIN completion_proofs cp
            ON cp.run = cm.completion
        WHERE lbm.map = $1
            AND cm.accepted_by IS NOT NULL
            AND cm.deleted_on IS NULL
            AND cm.new_version IS NULL
        """,
        map_code,
    )
    if not len(payload):
        return []

    return parse_runs_payload(payload, full_usr_info=True)


@postgres
async def get_completions_for(
        code: str,
        formats: list[int],
        idx_start: int = 0,
        amount: int = 50,
        conn=None
) -> tuple[list[ListCompletion], int]:
    extra_args = []
    if len(formats):
        extra_args.append(formats)
    payload = await conn.fetch(
        f"""
        WITH runs_with_flags AS (
            SELECT
                c.id AS run_id,
                r.id AS meta_id,
                lccs.id AS lcc_id,
                c.*,
                r.*,
                (r.lcc = lccs.id AND lccs.id IS NOT NULL) AS current_lcc,
                lccs.leftover
            FROM completions_meta r
            JOIN completions c
                ON r.completion = c.id
            LEFT JOIN lccs_by_map lccs
                ON lccs.id = r.lcc
            WHERE c.map = $1
                {'AND r.format = ANY($4::int[])' if len(formats) > 0 else ''}
                AND r.accepted_by IS NOT NULL
                AND r.deleted_on IS NULL
                AND r.new_version IS NULL
        ),
        unique_runs AS (
            SELECT DISTINCT ON (rwf.run_id)
                rwf.run_id, rwf.map, rwf.black_border, rwf.no_geraldo, rwf.current_lcc, rwf.format,
                ARRAY_AGG(cp.proof_url) FILTER(WHERE cp.proof_type = 0) OVER(PARTITION BY rwf.run_id) AS subm_proof_img,
                ARRAY_AGG(cp.proof_url) FILTER(WHERE cp.proof_type = 1) OVER(PARTITION BY rwf.run_id) AS subm_proof_vid,
                
                rwf.lcc_id AS lcc_id, rwf.leftover,
                
                ARRAY_AGG(ply.user_id) OVER (PARTITION by rwf.meta_id) AS user_ids,
                ARRAY_AGG(u.name) OVER (PARTITION by rwf.meta_id) AS user_names
            FROM runs_with_flags rwf
            JOIN comp_players ply
                ON ply.run = rwf.meta_id
            LEFT JOIN completion_proofs cp
                ON cp.run = rwf.run_id
            JOIN users u
                ON ply.user_id = u.discord_id
        )
        SELECT COUNT(*) OVER() AS total_count, uq.*
        FROM unique_runs uq
        ORDER BY
            uq.user_ids ASC,
            uq.black_border DESC,
            uq.no_geraldo DESC,
            uq.current_lcc DESC
        LIMIT $3
        OFFSET $2
        """,
        code, idx_start, amount, *extra_args,
    )

    return parse_runs_payload(payload, full_usr_info=True), payload[0][0] if len(payload) else 0


@postgres
async def map_exists(code, conn=None) -> bool:
    result = await conn.execute("SELECT code FROM maps WHERE code=$1", code)
    return int(result[len("SELECT "):]) > 0


@postgres
async def alias_exists(alias: str, conn=None) -> bool:
    result = await conn.execute(
        """
        SELECT al.alias
        FROM map_aliases al
        JOIN map_list_meta m
            ON m.code = al.map
        WHERE al.alias=$1
            AND m.deleted_on IS NULL
            AND m.new_version IS NULL
        """,
        alias,
    )
    return int(result[len("SELECT "):]) > 0


@postgres
async def insert_map_relations(map_id: str, map_data: dict, conn=None) -> None:
    await conn.executemany(
        "INSERT INTO additional_codes(code, description, belongs_to) VALUES ($1, $2, $3)",
        [
            (obj["code"], obj["description"], map_id)
            for obj in map_data["additional_codes"]
        ]
    )
    await conn.executemany(
        """
        INSERT INTO creators(map, user_id, role)
        VALUES ($1, $2, $3)
        ON CONFLICT DO NOTHING
        """,
        [
            (map_id, int(obj["id"]), obj["role"])
            for obj in map_data["creators"]
        ]
    )
    await conn.executemany(
        """
        INSERT INTO verifications(map, user_id, version)
        VALUES ($1, $2, $3)
        ON CONFLICT DO NOTHING
        """,
        [
            (map_id, int(obj["id"]), obj["version"])
            for obj in map_data["verifiers"]
        ]
    )
    await conn.executemany(
        "INSERT INTO mapver_compatibilities(map, version, status) VALUES ($1, $2, $3)",
        [
            (map_id, obj["version"], obj["status"])
            for obj in map_data["version_compatibilities"]
        ]
    )

    await conn.execute(
        """
        DELETE FROM map_aliases al
        USING maps m
        WHERE al.alias = ANY($1::VARCHAR(20)[])
        """,
        map_data["aliases"],
    )
    await conn.executemany(
        "INSERT INTO map_aliases(map, alias) VALUES ($1, $2)",
        [(map_id, alias) for alias in map_data["aliases"]]
    )


@postgres
async def delete_map_relations(map_id: str, conn=None) -> None:
    relations = [
        ("additional_codes", "belongs_to"),
        ("creators", "map"),
        ("verifications", "map"),
        ("mapver_compatibilities", "map"),
        ("map_aliases", "map"),
    ]
    coros = [
        conn.execute(f"DELETE FROM {table} WHERE {fkey}=$1", map_id)
        for table, fkey in relations
    ]
    for coro in coros:
        await coro


@postgres
async def add_map(map_data: dict, conn=None) -> None:
    async with conn.transaction():
        await update_list_placements(
            cur_positions=None if "placement_curver" not in map_data else (None,  map_data["placement_curver"]),
            all_positions=None if "placement_allver" not in map_data else (None,  map_data["placement_allver"]),
            conn=conn,
        )

        await conn.execute(
            """
            INSERT INTO maps(
                code, name, placement_allver, placement_curver, difficulty,
                map_data, r6_start, optimal_heros, map_preview_url
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
            map_data["code"], map_data["name"], map_data.get("placement_allver", -1),
            map_data.get("placement_curver", -1), map_data["difficulty"], map_data["map_data"],
            map_data["r6_start"], ";".join(map_data["optimal_heros"]), map_data["map_preview_url"],
        )

        await insert_map_relations(map_data["code"], map_data, conn=conn)


@postgres
async def edit_map(
        map_data: dict,
        map_current: PartialMap | None = None,
        conn=None
) -> None:
    map_data["optimal_heros"] = ";".join(map_data["optimal_heros"])
    if not map_current:
        map_current = await get_map(map_data["code"], partial=True, conn=conn)

    async with conn.transaction():
        await update_list_placements(
            cur_positions=None if "placement_curver" not in map_data else (map_current.placement_cur, map_data["placement_curver"]),
            all_positions=None if "placement_allver" not in map_data else (map_current.placement_all, map_data["placement_allver"]),
            conn=conn,
        )

        fields = [
            field for field in [
                "name",
                "placement_allver",
                "placement_curver",
                "difficulty",
                "map_data",
                "r6_start",
                "optimal_heros",
                "map_preview_url",
            ] if field in map_data
        ]

        field_format = "{}=${}"
        await conn.execute(
            f"""
            UPDATE maps
            SET
                {", ".join([
                    field_format.format(field, i+2)
                    for i, field in enumerate(fields)
                ] + ["deleted_on=NULL"])}
            WHERE code=$1
            """,
            map_data["code"],
            *[map_data.get(field) for field in fields],
        )

        await delete_map_relations(map_current.id, conn=conn)
        await insert_map_relations(map_current.id, map_data, conn=conn)


def normalize_positions(pos: tuple[int | None, int | None]) -> tuple[int, int]:
    big_number = 1_000_000
    return (
        pos[0] if pos[0] else big_number,
        pos[1] if pos[1] else big_number,
    )


@postgres
async def update_list_placements(
        cur_positions: tuple[int | None, int | None] | None = None,
        all_positions: tuple[int | None, int | None] | None = None,
        conn=None
) -> None:
    if cur_positions is not None and cur_positions[0] == cur_positions[1]:
        cur_positions = None
    if all_positions is not None and all_positions[0] == all_positions[1]:
        all_positions = None
    if cur_positions is all_positions is None:
        return

    selectors = []
    if cur_positions:
        selectors.append("placement_curver BETWEEN LEAST($1::int, $2::int) AND GREATEST($1::int, $2::int)")
    if all_positions:
        selectors.append("placement_allver BETWEEN LEAST($3::int, $4::int) AND GREATEST($3::int, $4::int)")
    await conn.execute(
        f"""
        INSERT INTO map_list_meta
            (placement_curver, placement_allver, code, difficulty, botb_difficulty, optimal_heros)
        SELECT
            {
                "placement_curver"
                if cur_positions is None else
                "CASE WHEN (placement_curver BETWEEN LEAST($1::int, $2::int) AND GREATEST($1::int, $2::int) "
                "   AND placement_curver != $1::int)"
                "THEN placement_curver + SIGN($1::int - $2::int) "
                "ELSE placement_curver END"
            },
            {
                "placement_allver"
                if cur_positions is None else
                "CASE WHEN (placement_allver BETWEEN LEAST($3::int, $4::int) AND GREATEST($3::int, $4::int) "
                "   AND placement_allver != $3::int)"
                "THEN placement_allver + SIGN($3::int - $4::int) "
                "ELSE placement_allver END"
            },
            code, difficulty, botb_difficulty, optimal_heros
        FROM map_list_meta mlm
        WHERE mlm.new_version IS NULL
            AND mlm.deleted_on IS NULL
            AND ({" OR ".join(selectors)})
        """,
        *(normalize_positions(cur_positions) if cur_positions else (None, None)),
        *(normalize_positions(all_positions) if all_positions else (None, None)),
    )

    await conn.execute(
        """
        UPDATE map_list_meta mlm_old
        SET
            new_version = mlm_new.id
        FROM map_list_meta mlm_new
        WHERE mlm_old.new_version IS NULL AND mlm_new.new_version IS NULL
            AND mlm_old.deleted_on IS NULL AND mlm_new.deleted_on IS NULL
            AND mlm_old.code = mlm_new.code
            AND mlm_old.created_on < mlm_new.created_on
        """
    )

    # await conn.execute(
    #     f"""
    #     UPDATE map_list_data
    #     SET {field} = {field} + SIGN($1::int - $2::int)
    #     WHERE {field} BETWEEN LEAST($1::int, $2::int) AND GREATEST($1::int, $2::int)
    #     """,
    #     old_pos, new_pos
    # )


@postgres
async def delete_map(
        code: str,
        *,
        map_current: PartialMap | None = None,
        modify_diff: bool = False,
        modify_pos: bool = False,
        modify_botb: bool = False,
        conn=None
) -> None:
    if not (modify_diff or modify_pos or modify_botb):
        return

    if not map_current:
        map_current = await get_map(code, partial=True, conn=conn)


    print("BEFORE")
    [print(x) for x in await conn.fetch(
        """SELECT * FROM map_list_meta WHERE code = 'MLXXXEJ'"""
    )]

    async with conn.transaction():
        indexes = [
            map_current.placement_cur,
            map_current.placement_all,
            map_current.difficulty,
            map_current.botb_difficulty,
        ]
        if modify_pos:
            await update_list_placements(
                cur_positions=(map_current.placement_cur, None),
                all_positions=(map_current.placement_all, None),
                conn=conn,
            )
            indexes[0] = None
            indexes[1] = None
        if modify_diff:
            indexes[2] = None
        if modify_botb:
            indexes[3] = None

        meta_id = await conn.fetchval(
            f"""
            INSERT INTO map_list_meta
                (placement_curver, placement_allver, difficulty, botb_difficulty, code, deleted_on, optimal_heros)
            SELECT
                $2, $3, $4, $5, $1::varchar(10),
                {"CURRENT_TIMESTAMP" if all([x is None for x in indexes]) else "NULL"},
                mlm.optimal_heros
            FROM map_list_meta mlm
            WHERE mlm.new_version IS NULL
                AND mlm.deleted_on IS NULL
                AND mlm.code = $1::varchar(10)
            RETURNING id
            """,
            code,
            *indexes,
        )

        await conn.execute(
            """
            UPDATE map_list_meta
            SET new_version = $1
            WHERE new_version IS NULL
                AND deleted_on IS NULL
                AND code = $2
                AND id != $1
            """,
            meta_id, code
        )

        print("AFTER")
        [print(x) for x in await conn.fetch(
            """SELECT * FROM map_list_meta WHERE code = 'MLXXXEJ'"""
        )]


@postgres
async def get_legacy_maps(conn=None) -> list[PartialListMap]:
    """
    Gets deleted maps or maps that were pushed off the list.
    A deleted map shows up only if it's not in any list.
    """
    payload = await conn.fetch(f"""
        WITH config_vars AS (
            SELECT
                ({get_int_config("current_btd6_ver")}) AS current_btd6_ver,
                ({get_int_config("map_count")}) AS map_count
        ),
        verified_current AS (
            SELECT map, (COUNT(map) > 0) AS is_verified
            FROM verifications
            CROSS JOIN config_vars
            WHERE version=current_btd6_ver
            GROUP BY map
        )
        SELECT
            name,
            m.code,
            is_verified IS NOT NULL AS is_verified,
            placement_curver,
            map_preview_url
        FROM maps m
        JOIN map_list_meta mlm
            ON m.code = mlm.code
        LEFT JOIN verified_current vc
            ON m.code=vc.map
        CROSS JOIN config_vars cvar
        WHERE mlm.new_version IS NULL AND
            (
                placement_curver > cvar.map_count
                OR placement_curver IS NULL
                    AND difficulty IS NULL
                    AND botb_difficulty IS NULL
            )
        ORDER BY
            (placement_curver IS NULL),
            placement_curver ASC
        """,
    )

    return [
        PartialListMap(
            row["name"],
            row["code"],
            row["placement_curver"],
            row["is_verified"],
            row["map_preview_url"],
        )
        for row in payload
    ]
