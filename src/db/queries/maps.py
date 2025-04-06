import asyncio
import src.db.connection
from src.db.models import (
    MinimalMap,
    PartialMap,
    Map,
    LCC,
    ListCompletion,
    PartialUser,
    RetroMap,
)
from src.db.queries.subqueries import get_int_config
from src.utils.misc import list_rm_dupe
from src.utils.formats.formats import format_keys
postgres = src.db.connection.postgres


@postgres
async def get_list_maps(
        conn: "asyncpg.pool.PoolConnectionProxy" = None,
        curver: bool = True
) -> list[MinimalMap]:
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
            vc.map IS NOT NULL AS is_verified,
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
        MinimalMap(
            row["name"],
            row["code"],
            row[placement_vname],
            row["is_verified"],
            row["map_preview_url"],
        )
        for row in payload
    ]


@postgres
async def get_maps_by_idx(
        idx: str = None,
        filter_val: int | None = None,
        conn: "asyncpg.pool.PoolConnectionProxy" = None,
) -> list[MinimalMap]:
    allowed_keys = ["difficulty", "botb_difficulty"]
    if idx not in allowed_keys:
        return []

    args = []
    if filter_val is not None:
        args.append(filter_val)
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
            mlm.{idx},
            m.map_preview_url,
            vc.map IS NOT NULL AS is_verified
        FROM maps m
        JOIN map_list_meta mlm
            ON mlm.code = m.code
        LEFT JOIN verified_current vc
            ON m.code = vc.map
        WHERE {idx} IS NOT NULL
            AND deleted_on IS NULL
            AND new_version IS NULL
            {("AND mlm." + idx + " = $1") if filter_val is not None else ""}
        """,
        *args,
    )

    return [
        MinimalMap(
            row["name"],
            row["code"],
            row[idx],
            row["is_verified"],
            row["map_preview_url"],
        )
        for row in payload
    ]


@postgres
async def get_nostalgia_pack(
        filter_val: int | None = None,
        conn: "asyncpg.pool.PoolConnectionProxy" = None,
) -> list[MinimalMap]:
    payload = await conn.fetch(
        f"""
        WITH verified_current AS (
            SELECT DISTINCT map
            FROM verifications
            WHERE version = ({get_int_config("current_btd6_ver")})
            GROUP BY map
        )
        SELECT
            rm.name,
            m.code,
            m.map_preview_url,
            vc.map IS NOT NULL AS is_verified,
            
            rm.id AS retro_map_id,
            rm.sort_order, rm.preview_url AS retro_map_preview_url,
            rg.game_id, rg.category_id, rg.subcategory_id,
            rg.game_name, rg.category_name, rg.subcategory_name
        FROM maps m
        JOIN map_list_meta mlm
            ON mlm.code = m.code
        LEFT JOIN verified_current vc
            ON m.code = vc.map
        RIGHT JOIN retro_maps rm
            ON rm.id = mlm.remake_of
        JOIN retro_games rg
            ON rm.game_id = rg.game_id
            AND rm.category_id = rg.category_id
            AND rm.subcategory_id = rg.subcategory_id
        WHERE rm.game_id = $1
            AND deleted_on IS NULL
            AND new_version IS NULL
        """,
        filter_val,
    )

    return [
        MinimalMap(
            row["name"],
            row["code"],
            RetroMap(
                row["retro_map_id"],
                row["name"],
                row["sort_order"],
                row["retro_map_preview_url"],
                row["game_id"],
                row["category_id"],
                row["subcategory_id"],
                row["game_name"],
                row["category_name"],
                row["subcategory_name"],
            ),
            row["is_verified"],
            row["map_preview_url"],
        )
        for row in payload
    ]


@postgres
async def get_map(code: str, partial: bool = False, conn=None) -> Map | PartialMap | None:
    columns = """
        m.code, m.name, mlm.placement_curver, mlm.placement_allver, mlm.difficulty, m.r6_start,
        m.map_data, mlm.deleted_on, mlm.optimal_heros, m.map_preview_url, mlm.botb_difficulty,
        mlm.remake_of
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
            WHERE mlm.placement_allver = $1::int
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
                
                UNION

                (
                    SELECT 7 AS ord, {columns}
                    FROM maps m
                    JOIN map_list_meta mlm
                        ON m.code = mlm.code
                    WHERE LOWER(m.name) = LOWER($1)
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
            m.optimal_heros, m.map_preview_url, m.botb_difficulty,
            m.remake_of
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
            pl_map["remake_of"],
            pl_map["r6_start"],
            pl_map["map_data"],
            pl_map["deleted_on"],
            pl_map["optimal_heros"].split(";"),
            pl_map["map_preview_url"],
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
        None if pl_map["remake_of"] is None else await get_retro_map(pl_map["remake_of"], conn=conn),
        pl_map["r6_start"],
        pl_map["map_data"],
        pl_map["deleted_on"],
        pl_map["optimal_heros"].split(";"),
        pl_map["map_preview_url"],
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
                PartialUser(run["user_ids"][i], run["user_names"][i], None, False, False)
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
                
                -- This only fetches the largest leftover.
                -- To fetch leftover for all runs, join with leastcostchimps here.
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
async def map_exists_in_format(
        map_code: str,
        format_id: int,
        conn: "asyncpg.pool.PoolConnectionProxy" = None
) -> bool:
    result = await conn.execute(
        f"""
        SELECT m.code
        FROM maps m
        JOIN map_list_meta mlm
            ON mlm.code = m.code
        WHERE m.code = $1
            AND mlm.{format_keys[format_id]} IS NOT NULL
            AND mlm.new_version IS NULL
            AND mlm.deleted_on IS NULL
        """,
        map_code
    )
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
async def set_map_relations(map_code: str, map_data: dict, conn=None) -> None:
    await conn.execute(
        """
        CREATE TEMP TABLE tmp_additional_codes (
            code VARCHAR(10),
            description TEXT,
            belongs_to VARCHAR(10)
        ) ON COMMIT DROP;
        
        CREATE TEMP TABLE tmp_creators (
            user_id BIGINT,
            role TEXT,
            map VARCHAR(10)
        ) ON COMMIT DROP;
        
        CREATE TEMP TABLE tmp_verifications (
            user_id BIGINT,
            version INT,
            map VARCHAR(10)
        ) ON COMMIT DROP;
        
        CREATE TEMP TABLE tmp_mapver_compatibilities (
            version INT,
            status INT,
            map VARCHAR(10)
        ) ON COMMIT DROP;
        
        CREATE TEMP TABLE tmp_map_aliases (
            alias VARCHAR(255),
            map VARCHAR(10)
        ) ON COMMIT DROP;
        """
    )

    queries = """
        INSERT INTO tmp_additional_codes
            (code, description, belongs_to)
        VALUES
            ($1, $2, $3)
        ;
        INSERT INTO tmp_creators
            (map, user_id, role)
        VALUES
            ($1, $2, $3)
        ;
        INSERT INTO tmp_verifications
            (map, user_id, version)
        VALUES
            ($1, $2, $3)
        ;
        INSERT INTO tmp_mapver_compatibilities
            (map, version, status)
        VALUES ($1, $2, $3)
        ;
        INSERT INTO tmp_map_aliases
            (map, alias)
        VALUES
            ($1, $2)
    """.split(";")

    q_params = [
        [(obj["code"], obj["description"], map_code)
         for obj in map_data["additional_codes"]],
        [(map_code, int(obj["id"]), obj["role"])
         for obj in map_data["creators"]],
        [(map_code, int(obj["id"]), obj["version"])
         for obj in map_data["verifiers"]],
        [(map_code, obj["version"], obj["status"])
         for obj in map_data["version_compatibilities"]],
        [(map_code, alias) for alias in map_data["aliases"]],
    ]

    for query, params in zip(queries, q_params):
        await conn.executemany(query, params)

    queries = """
        DELETE FROM additional_codes
        WHERE code IN (
            SELECT ac.code
            FROM additional_codes ac
            LEFT JOIN tmp_additional_codes tac
                ON ac.code = tac.code
            WHERE tac.code IS NULL
                AND ac.belongs_to = $1
        )
        ;
        DELETE FROM creators
        WHERE (map, user_id) IN (
            SELECT c.map, c.user_id
            FROM creators c
            LEFT JOIN tmp_creators tc
                ON c.map = tc.map
                AND c.user_id = tc.user_id
            WHERE tc.map IS NULL
                AND c.map = $1
        )
        ;
        DELETE FROM verifications
        WHERE (map, user_id, COALESCE(version, -1)) IN (
            SELECT v.map, v.user_id, COALESCE(v.version, -1)
            FROM verifications v
            LEFT JOIN tmp_verifications tv
                ON v.map = tv.map
                AND v.user_id = tv.user_id
                AND v.version = tv.version
            WHERE tv.map IS NULL
                AND v.map = $1
        )
        ;
        DELETE FROM mapver_compatibilities
        WHERE (map, version) IN (
            SELECT c.map, c.version
            FROM mapver_compatibilities c
            LEFT JOIN tmp_mapver_compatibilities tc
                ON c.map = tc.map
                AND c.version = tc.version
            WHERE tc.map IS NULL
                AND c.map = $1
        )
        ;
        DELETE FROM map_aliases
        WHERE (map, alias) IN (
            SELECT a.map, a.alias
            FROM map_aliases a
            LEFT JOIN tmp_map_aliases ta
                ON a.alias = ta.alias
            WHERE ta.alias IS NULL
                AND a.map = $1
        )
    """.split(";")

    for query in queries:
        await conn.execute(query, map_code)

    await conn.execute(
        """
        UPDATE additional_codes ac
        SET
            description = tac.description,
            belongs_to = tac.belongs_to
        FROM tmp_additional_codes tac
        WHERE tac.code = ac.code
        ;
        INSERT INTO additional_codes
            (code, description, belongs_to)
        SELECT
            tac.code, tac.description, tac.belongs_to
        FROM tmp_additional_codes tac
        LEFT JOIN additional_codes ac
            ON tac.code = ac.code
        WHERE ac.code IS NULL
        ;
        
        UPDATE creators c
        SET
            role = tc.role
        FROM tmp_creators tc
        WHERE tc.map = c.map
            AND tc.user_id = c.user_id
        ;
        INSERT INTO creators
            (map, user_id, role)
        SELECT
            tc.map, tc.user_id, tc.role
        FROM tmp_creators tc
        LEFT JOIN creators c
            ON tc.map = c.map
            AND tc.user_id = c.user_id
        WHERE c.map IS NULL
        ;
        
        INSERT INTO verifications
            (map, user_id, version)
        SELECT
            tv.map, tv.user_id, tv.version
        FROM tmp_verifications tv
        LEFT JOIN verifications v
            ON tv.map = v.map
            AND tv.user_id = v.user_id
            AND tv.version = v.version
        WHERE v.map IS NULL
        ;
        
        UPDATE mapver_compatibilities v
        SET
            status = tv.status
        FROM tmp_mapver_compatibilities tv
        WHERE tv.map = v.map
            AND tv.version = v.version
        ;
        INSERT INTO mapver_compatibilities
            (map, status, version)
        SELECT
            tv.map, tv.status, tv.version
        FROM tmp_mapver_compatibilities tv
        LEFT JOIN verifications v
            ON tv.map = v.map
            AND tv.version = v.version
        WHERE v.map IS NULL
        ;
        
        UPDATE map_aliases a
        SET
            map = ta.map
        FROM tmp_map_aliases ta
        WHERE ta.alias = a.alias
        ;
        INSERT INTO map_aliases
            (map, alias)
        SELECT
            ta.map, ta.alias
        FROM tmp_map_aliases ta
        LEFT JOIN map_aliases a
            ON ta.alias = a.alias
        WHERE a.alias IS NULL
        ;
        """
    )

    if map_data.get("remake_of") and \
            (prev_remake_of := await get_remake_of_code(map_data.get("remake_of"))):
        await set_map_list_meta(prev_remake_of, remake_of=None, conn=conn)
    meta_id = await set_map_list_meta(map_code, **map_data, conn=conn)
    if meta_id:
        await link_new_version(conn=conn)


@postgres
async def get_remake_of_code(
        retro_map_id: int,
        conn: "asyncpg.pool.PoolConnectionProxy" = None,
) -> str:
    map_code = await conn.fetchrow(
        """
        SELECT 
            code
        FROM map_list_meta
        WHERE remake_of = $1
            AND new_version IS NULL
            AND deleted_on IS NULL
        """,
        retro_map_id
    )
    return map_code["code"] if map_code else None


@postgres
async def set_map_list_meta(
        map_code: str,
        conn: "asyncpg.pool.PoolconnectionProxy" = None,
        **kwargs
) -> int:
    return await conn.fetchval(
        f"""
            INSERT INTO map_list_meta
                (code, optimal_heros, placement_curver, placement_allver, difficulty, botb_difficulty, remake_of)

            SELECT
                $1::varchar(10),
                {"$2::text" if "optimal_heros" in kwargs else "optimal_heros"},
                {"$3::int" if "placement_curver" in kwargs else "placement_curver"},
                {"$4::int" if "placement_allver" in kwargs else "placement_allver"},
                {"$5::int" if "difficulty" in kwargs else "difficulty"},
                {"$6::int" if "botb_difficulty" in kwargs else "botb_difficulty"},
                {"$7::int" if "remake_of" in kwargs else "remake_of"}
            FROM map_list_meta
            WHERE code = $1::varchar(10)
                AND new_version IS NULL
                AND deleted_on IS NULL

            UNION ALL

            SELECT
                $1::varchar(10), 
                $2,
                $3,
                $4,
                $5,
                $6,
                $7

            LIMIT 1
            RETURNING id
            """,
        map_code,
        ";".join(kwargs.get("optimal_heros", [])),
        kwargs.get("placement_curver", None),
        kwargs.get("placement_allver", None),
        kwargs.get("difficulty", None),
        kwargs.get("botb_difficulty", None),
        kwargs.get("remake_of", None),
    )


@postgres
async def add_map(map_data: dict, conn=None) -> None:
    async with conn.transaction():
        await update_list_placements(
            cur_positions=None if "placement_curver" not in map_data else (None,  map_data["placement_curver"]),
            all_positions=None if "placement_allver" not in map_data else (None,  map_data["placement_allver"]),
            ignore_code=map_data["code"],
            conn=conn,
        )

        await conn.execute(
            """
            INSERT INTO maps
                (code, name, map_data, r6_start, map_preview_url)
            VALUES
                ($1, $2, $3, $4, $5)
            """,
            map_data["code"], map_data["name"], map_data["map_data"],
            map_data["r6_start"], map_data["map_preview_url"],
        )

        await set_map_relations(map_data["code"], map_data, conn=conn)


@postgres
async def edit_map(
        map_data: dict,
        map_current: PartialMap | None = None,
        conn=None
) -> None:
    if not map_current:
        map_current = await get_map(map_data["code"], partial=True, conn=conn)

    async with conn.transaction():
        await update_list_placements(
            cur_positions=None if "placement_curver" not in map_data else (map_current.placement_curver, map_data["placement_curver"]),
            all_positions=None if "placement_allver" not in map_data else (map_current.placement_allver, map_data["placement_allver"]),
            ignore_code=map_data["code"],
            conn=conn,
        )

        await conn.execute(
            f"""
            UPDATE maps
            SET
                name = $2,
                map_data = $3,
                r6_start = $4,
                map_preview_url = $5
            WHERE code=$1
            """,
            map_data["code"], map_data["name"], map_data["map_data"], map_data["r6_start"],
            map_data["map_preview_url"],
        )

        await set_map_relations(map_current.code, map_data, conn=conn)


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
        ignore_code: str | None = None,
        conn=None
) -> None:
    if cur_positions is not None and cur_positions[0] == cur_positions[1]:
        cur_positions = None
    if all_positions is not None and all_positions[0] == all_positions[1]:
        all_positions = None
    if cur_positions is all_positions is None:
        return

    selectors = []
    args = []
    base_idx = 2

    curver_selector = "placement_curver"
    if cur_positions:
        selectors.append(f"placement_curver BETWEEN LEAST(${base_idx}::int, ${base_idx+1}::int) AND GREATEST(${base_idx}::int, ${base_idx+1}::int)")
        curver_selector = f"""
            CASE WHEN (placement_curver BETWEEN LEAST(${base_idx}::int, ${base_idx+1}::int) AND GREATEST(${base_idx}::int, ${base_idx+1}::int))
            THEN placement_curver + SIGN(${base_idx}::int - ${base_idx+1}::int)
            ELSE placement_curver END
        """
        args += [*normalize_positions(cur_positions)]
        base_idx += 2

    allver_selector = "placement_allver"
    if all_positions:
        selectors.append(f"placement_allver BETWEEN LEAST(${base_idx}::int, ${base_idx+1}::int) AND GREATEST(${base_idx}::int, ${base_idx+1}::int)")
        allver_selector = f"""
            CASE WHEN (placement_allver BETWEEN LEAST(${base_idx}::int, ${base_idx + 1}::int) AND GREATEST(${base_idx}::int, ${base_idx + 1}::int))
            THEN placement_allver + SIGN(${base_idx}::int - ${base_idx + 1}::int)
            ELSE placement_allver END
        """
        args += [*normalize_positions(all_positions)]
        base_idx += 2

    await conn.execute(
        f"""
        INSERT INTO map_list_meta
            (placement_curver, placement_allver, code, difficulty, botb_difficulty, optimal_heros)
        SELECT
            {curver_selector},
            {allver_selector},
            code, difficulty, botb_difficulty, optimal_heros
        FROM map_list_meta mlm
        WHERE mlm.new_version IS NULL
            AND mlm.deleted_on IS NULL
            AND ({" OR ".join(selectors)})
            AND mlm.code != $1
        """,
        ignore_code,
        *args,
    )

    await link_new_version(conn=conn)


@postgres
async def link_new_version(conn=None) -> None:
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


@postgres
async def delete_map(
        code: str,
        *,
        map_current: PartialMap | None = None,
        keys: list[str] = None,
        conn: "asyncpg.pool.PoolConnectionProxy" = None,
) -> None:
    if not map_current:
        map_current = await get_map(code, partial=True, conn=conn)

    async with conn.transaction():
        key_order = [format_keys[k] for k in format_keys]
        unchanged = [key for key in key_order if key not in keys]

        meta_id, plc_cur, plc_all = await conn.fetchrow(
            f"""
            INSERT INTO map_list_meta
                ({", ".join(key_order)}, code, deleted_on, optimal_heros)
            SELECT
                {", ".join([
                    "NULL" if key in keys else key
                    for key in key_order
                ])},
                $1::varchar(10),
                CASE WHEN ({" AND ".join([
                        key + " IS NULL"
                        for key in unchanged
                    ]) if len(unchanged) else "TRUE"})
                    THEN CURRENT_TIMESTAMP
                    ELSE NULL
                END,
                mlm.optimal_heros
            FROM map_list_meta mlm
            WHERE mlm.new_version IS NULL
                AND mlm.deleted_on IS NULL
                AND mlm.code = $1::varchar(10)
            RETURNING id, placement_allver, placement_curver
            """,
            code,
        )

        await update_list_placements(
            cur_positions=(map_current.placement_curver, None) if plc_cur is None else None,
            all_positions=(map_current.placement_allver, None) if plc_all is None else None,
            ignore_code=code,
            conn=conn,
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


@postgres
async def get_legacy_maps(conn=None) -> list[MinimalMap]:
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
        MinimalMap(
            row["name"],
            row["code"],
            row["placement_curver"],
            row["is_verified"],
            row["map_preview_url"],
        )
        for row in payload
    ]


@postgres
async def get_retro_maps(conn: "asyncpg.pool.PoolConnectionProxy" = None) -> list[RetroMap]:
    payload = await conn.fetch(
        """
        SELECT
            rm.name, rm.id, rm.sort_order, rm.preview_url, rm.game_id, rm.category_id, rm.subcategory_id,
            rg.game_name, rg.category_name, rg.subcategory_name
        FROM retro_maps rm
        JOIN retro_games rg
            ON rm.game_id = rg.game_id
            AND rm.category_id = rg.category_id
            AND rm.subcategory_id = rg.subcategory_id
        """,
    )

    return [
        RetroMap(
            row["id"],
            row["name"],
            row["sort_order"],
            row["preview_url"],
            row["game_id"],
            row["category_id"],
            row["subcategory_id"],
            row["game_name"],
            row["category_name"],
            row["subcategory_name"],
        )
        for row in payload
    ]


@postgres
async def get_retro_map(map_id: int, conn: "asyncpg.pool.PoolConnectionProxy" = None) -> RetroMap | None:
    payload = await conn.fetchrow(
        """
        SELECT
            rm.name, rm.id, rm.sort_order, rm.preview_url, rm.game_id, rm.category_id, rm.subcategory_id,
            rg.game_name, rg.category_name, rg.subcategory_name
        FROM retro_maps rm
        JOIN retro_games rg
            ON rm.game_id = rg.game_id
            AND rm.category_id = rg.category_id
            AND rm.subcategory_id = rg.subcategory_id
        WHERE id = $1
        """,
        map_id
    )

    return None if payload is None else RetroMap(
        map_id,
        payload["name"],
        payload["sort_order"],
        payload["preview_url"],
        payload["game_id"],
        payload["category_id"],
        payload["subcategory_id"],
        payload["game_name"],
        payload["category_name"],
        payload["subcategory_name"],
    )
