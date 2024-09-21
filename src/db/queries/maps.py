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
            SELECT map, (COUNT(map) > 0) AS is_verified
            FROM verifications
            CROSS JOIN config_vars
            WHERE version=current_btd6_ver
            GROUP BY map
        )
        SELECT
            name,
            m.code,
            is_verified IS NOT NULL,
            placement_allver,
            placement_curver,
            map_preview_url
        FROM maps m
        LEFT JOIN verified_current vc
            ON m.id=vc.map
        CROSS JOIN config_vars cvar
        WHERE {placement_vname} BETWEEN 1 AND cvar.map_count
            AND deleted_on IS NULL
        ORDER BY {placement_vname} ASC
    """, )
    return [
        PartialListMap(row[0], row[1], row[3 + int(curver)], row[2], row[5])
        for row in payload
    ]


@postgres
async def get_expert_maps(conn=None) -> list[PartialExpertMap]:
    payload = await conn.fetch("""
        SELECT name, code, difficulty, map_preview_url
        FROM maps
        WHERE difficulty > -1
            AND deleted_on IS NULL
    """)
    return [
        PartialExpertMap(row[0], row[1], row[2], row[3])
        for row in payload
    ]


@postgres
async def get_map(code: str, partial: bool = False, conn=None) -> Map | PartialMap | None:
    placement_union = ""
    if code.isnumeric():  # Current version index
        placement_union = """
            UNION
            SELECT m.* FROM maps m WHERE m.placement_curver = $1::int
        """
    elif code.startswith("@") and code[1:].isnumeric():  # All versions idx
        code = code[1:]
        placement_union = """
            UNION
            SELECT m.* FROM maps m WHERE m.placement_allver = $1::int
        """

    payload = await conn.fetch(
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
                SELECT m.* FROM maps m WHERE m.code = $1
                UNION
                SELECT m.* FROM maps m WHERE LOWER(m.name) = LOWER($1)
                UNION
                SELECT m.*
                FROM maps m
                JOIN map_aliases a
                    ON m.id = a.map
                WHERE LOWER(a.alias) = LOWER($1)
                {placement_union}
            ) possible
            LIMIT 1
        )
        SELECT
            m.code, m.name, m.placement_curver, m.placement_allver, m.difficulty,
            m.r6_start, m.map_data, v.is_verified, m.deleted_on,
            m.optimal_heros, m.map_preview_url, m.id, m.new_version, m.created_on
        FROM possible_map m
        LEFT JOIN verified_maps v
            ON v.map = m.id
        """,
        code,
    )
    if len(payload) == 0:
        return None

    pl_map = payload[0]
    map_id = pl_map[11]
    map_code = pl_map[0]
    if partial:
        return PartialMap(
            map_id,
            map_code,
            pl_map[1],
            pl_map[2],
            pl_map[3],
            pl_map[4],
            pl_map[5],
            pl_map[6],
            pl_map[8],
            pl_map[9].split(";"),
            pl_map[10],
            pl_map[12],
            pl_map[13],
        )

    lccs = await get_lccs_for(map_code, conn=conn)
    pl_codes = await conn.fetch("SELECT code, description FROM additional_codes WHERE belongs_to=$1", map_id)
    pl_creat = await conn.fetch(
        """
        SELECT user_id, role, name
        FROM creators c
        JOIN users u
            ON u.discord_id=c.user_id
        WHERE map=$1
        """,
        map_id,
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
        """,
        map_id
    )
    pl_compat = await conn.fetch("SELECT status, version FROM mapver_compatibilities WHERE map=$1", map_id)
    pl_aliases = await conn.fetch("SELECT alias FROM map_aliases WHERE map=$1", map_id)

    return Map(
        map_id,
        map_code,
        pl_map[1],
        pl_map[2],
        pl_map[3],
        pl_map[4],
        pl_map[5],
        pl_map[6],
        pl_map[8],
        pl_map[9].split(";"),
        pl_map[10],
        pl_map[12],
        pl_map[13],
        [(row[0], row[1], row[2]) for row in pl_creat],
        pl_codes,
        [(uid, ver/10 if ver else None, name) for uid, ver, name in pl_verif],
        pl_map[7],
        lccs,
        pl_compat,
        [row[0] for row in pl_aliases],
    )


def parse_runs_payload(
        payload,
        has_count: bool = True,
        full_usr_info: bool = False,
) -> list[ListCompletion]:
    run_idx = 0 + int(has_count)
    lcc_idx = 6 + int(has_count)
    agg_idx = 9 + int(has_count)

    comps = []
    for run in payload:
        usr_list = list(set(run[agg_idx]))
        if full_usr_info:
            usrname_list = list(set(run[agg_idx+1]))
            usr_list = [
                PartialUser(usr_list[i], usrname_list[i], None, False)
                for i in range(len(usr_list))
            ]

        comps.append(ListCompletion(
            run[run_idx],
            run[run_idx + 1],
            usr_list,
            run[run_idx + 2],
            run[run_idx + 3],
            run[run_idx + 4],
            run[run_idx + 5],
            LCC(*run[lcc_idx:agg_idx]) if run[lcc_idx] else None,
        ))
    return comps


@postgres
async def get_lccs_for(map_code: str, conn=None) -> list[ListCompletion]:
    payload = await conn.fetch(
        """
        SELECT
            runs.id, runs.map, runs.black_border, runs.no_geraldo, TRUE,
            runs.format,

            lccs.id, lccs.proof, lccs.leftover,

            ARRAY_AGG(ply.user_id) OVER (PARTITION by runs.id) AS user_ids,
            ARRAY_AGG(u.name) OVER (PARTITION by runs.id) AS user_names
        FROM list_completions runs
        JOIN lccs_by_map lbm
            ON lbm.id = runs.lcc
        JOIN leastcostchimps lccs
            ON runs.lcc = lccs.id
        JOIN listcomp_players ply
            ON ply.run = runs.id
        JOIN users u
            ON ply.user_id = u.discord_id
        WHERE runs.map = $1
            AND runs.accepted_by IS NOT NULL
            AND runs.deleted_on IS NULL
        """,
        map_code,
    )
    if not len(payload):
        return []

    return parse_runs_payload(payload, has_count=False, full_usr_info=True)


@postgres
async def get_completions_for(code, idx_start=0, amount=50, conn=None) -> tuple[list[ListCompletion], int]:
    payload = await conn.fetch(
        f"""
        WITH runs_with_flags AS (
            SELECT r.*, (r.lcc = lccs.id AND lccs.id IS NOT NULL) AS current_lcc
            FROM list_completions r
            LEFT JOIN lccs_by_map lccs
                ON lccs.id = r.lcc
            WHERE r.map = $1
                AND r.accepted_by IS NOT NULL
                AND r.deleted_on IS NULL
        ),
        unique_runs AS (
            SELECT DISTINCT ON (rwf.id)
                rwf.id, rwf.map, rwf.black_border, rwf.no_geraldo, rwf.current_lcc,
                rwf.format,
                
                lccs.id, lccs.proof, lccs.leftover,
                
                ARRAY_AGG(ply.user_id) OVER (PARTITION by rwf.id) AS user_ids
            FROM runs_with_flags rwf
            JOIN listcomp_players ply
                ON ply.run = rwf.id
            LEFT JOIN leastcostchimps lccs
                ON rwf.lcc = lccs.id
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
        code, idx_start, amount,
    )

    return parse_runs_payload(payload), payload[0][0] if len(payload) else 0


@postgres
async def map_exists(code, conn=None) -> bool:
    result = await conn.execute("SELECT code FROM maps WHERE code=$1", code)
    return int(result[len("SELECT "):]) > 0


@postgres
async def alias_exists(alias, conn=None) -> bool:
    result = await conn.execute("SELECT alias FROM map_aliases WHERE alias=$1", alias)
    return int(result[len("SELECT "):]) > 0


@postgres
async def insert_map_relations(map_id: int, map_data: dict, conn=None) -> None:
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
    await conn.executemany(
        "INSERT INTO map_aliases(map, alias) VALUES ($1, $2)",
        [(map_id, alias) for alias in map_data["aliases"]]
    )


@postgres
async def delete_map_relations(map_id: int, conn=None) -> None:
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
        for field in ["placement_allver", "placement_curver"]:
            await update_list_placements(field, -1, map_data[field])

        map_id = await conn.fetchval(
            """
            INSERT INTO maps(
                code, name, placement_allver, placement_curver, difficulty,
                map_data, r6_start, optimal_heros, map_preview_url
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING id
            """,
            map_data["code"], map_data["name"], map_data["placement_allver"],
            map_data["placement_curver"], map_data["difficulty"], map_data["map_data"],
            map_data["r6_start"], ";".join(map_data["optimal_heros"]), map_data["map_preview_url"],
        )

        await insert_map_relations(map_id, map_data, conn=conn)


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
        for field, model_field in [("placement_allver", "placement_all"), ("placement_curver", "placement_cur")]:
            if field not in map_data:
                continue
            old_pos = getattr(map_current, model_field)
            new_pos = map_data[field]
            await update_list_placements(field, old_pos, new_pos, conn=conn)

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
                ])}
            WHERE code=$1
            """,
            map_data["code"],
            *[map_data.get(field) for field in fields],
        )

        await delete_map_relations(map_current.id, conn=conn)
        await insert_map_relations(map_current.id, map_data, conn=conn)


@postgres
async def update_list_placements(
        field: str,
        old_pos: int,
        new_pos: int,
        conn=None
) -> None:
    if old_pos == new_pos:
        return
    if old_pos == -1:
        old_pos = 1000
    elif new_pos == -1:
        new_pos = 1000

    await conn.execute(
        f"""
        UPDATE maps
        SET {field} = {field} + SIGN($1::int - $2::int)
        WHERE {field} BETWEEN LEAST($1::int, $2::int) AND GREATEST($1::int, $2::int)
        """,
        old_pos, new_pos
    )


@postgres
async def delete_map(
        code: str,
        *,
        map_current: PartialMap | None = None,
        modify_diff: bool = False,
        modify_pos: bool = False,
        conn=None
) -> None:
    if not (modify_diff or modify_pos):
        return

    if not map_current:
        map_current = await get_map(code, partial=True, conn=conn)

    updates = []
    indexes = [map_current.placement_cur, map_current.placement_all, map_current.difficulty]
    if modify_pos:
        updates += ["placement_curver=-1", "placement_allver=-1"]
        await update_list_placements("placement_curver", map_current.placement_cur, -1)
        await update_list_placements("placement_allver", map_current.placement_all, -1)
        indexes[0] = -1
        indexes[1] = -1
    if modify_diff:
        updates.append("difficulty=-1")
        indexes[2] = -1

    if all([x == -1 for x in indexes]):
        updates.append("deleted_on=CURRENT_TIMESTAMP")

    async with conn.transaction():
        await conn.execute(
            f"""
            UPDATE maps
            SET
                {", ".join(updates)}
            WHERE code=$1
            """,
            code
        )


@postgres
async def get_legacy_maps(conn=None) -> list[PartialListMap]:
    """
    Gets deleted maps or maps that were pushed off the list.
    A deleted map shows up only if it's not in the expert list.
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
            is_verified IS NOT NULL,
            placement_curver,
            map_preview_url
        FROM maps m
        LEFT JOIN verified_current vc
            ON m.id=vc.map
        CROSS JOIN config_vars cvar
        WHERE new_version IS NULL AND
            (
                placement_curver > cvar.map_count
                OR placement_curver = -1 AND difficulty = -1
            )
        ORDER BY placement_curver ASC
        """,
    )
    return [
        PartialListMap(row[0], row[1], row[3], row[2], row[4])
        for row in payload
    ]
