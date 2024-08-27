import asyncio
import src.db.connection
from src.db.models import (
    PartialListMap,
    PartialExpertMap,
    Map,
    LCC,
    ListCompletion
)
from src.db.queries.subqueries import get_int_config
from src.utils.misc import list_eq
postgres = src.db.connection.postgres


@postgres
async def get_list_maps(conn=None, curver=True) -> list[PartialListMap]:
    q_is_verified = f"""
        SELECT (COUNT(*) > 0)
        FROM verifications
        WHERE map=code
            AND version={get_int_config("current_btd6_ver")}
    """.strip()
    placement_vname = "placement_curver" if curver else "placement_allver"
    payload = await conn.fetch(f"""
        SELECT name, code, ({q_is_verified}) AS is_verified, placement_allver,
            placement_curver
        FROM maps
        WHERE {placement_vname} > -1
            AND {placement_vname} <= {get_int_config("map_count")}
        ORDER BY {placement_vname} ASC
    """, )
    return [
        PartialListMap(row[0], row[1], row[3 + int(curver)], row[2])
        for row in payload
    ]


@postgres
async def get_expert_maps(conn=None) -> list[PartialExpertMap]:
    payload = await conn.fetch("""
        SELECT name, code, difficulty
        FROM maps
        WHERE difficulty > -1
    """)
    return [
        PartialExpertMap(row[0], row[1], row[2])
        for row in payload
    ]


@postgres
async def get_map(code, conn=None) -> Map | None:
    q_is_verified = f"""
        SELECT COUNT(*) > 0
        FROM verifications
        WHERE map=$1
            AND version={get_int_config("current_btd6_ver")}
    """.strip()
    payload = await conn.fetch(f"""
        SELECT
            code, name, placement_curver, placement_allver, difficulty,
            r6_start, map_data, ({q_is_verified}) AS is_verified
        FROM maps
        WHERE code = $1
    """, code)
    if len(payload) == 0:
        return None
    pl_map = payload[0]

    lccs, pl_codes, pl_creat, pl_verif, pl_compat = await asyncio.gather(
        get_lccs_for(code),
        conn.fetch("SELECT code, description FROM additional_codes WHERE belongs_to=$1", code),
        conn.fetch("SELECT user_id, role FROM creators WHERE map=$1", code),
        conn.fetch(f"""
            SELECT user_id, version
            FROM verifications WHERE map=$1
                AND (version={get_int_config("current_btd6_ver")}
                OR version IS NULL)
        """, code),
        conn.fetch("SELECT status, version FROM mapver_compatibilities WHERE map=$1", code),
    )

    return Map(
        pl_map[0],
        pl_map[1],
        pl_map[2],
        pl_map[3],
        pl_map[4],
        pl_map[5],
        pl_map[6],
        [(row[0], row[1]) for row in pl_creat],
        pl_codes,
        [(uid, ver/10 if ver else None) for uid, ver in pl_verif],
        pl_map[7],
        lccs,
        pl_compat
    )


@postgres
async def get_lccs_for(code, conn=None) -> list[LCC]:
    payload = await conn.fetch(
        f"""
        WITH lcc_mins AS (
            SELECT format, MIN(leftover) AS leftover
            FROM leastcostchimps
            WHERE map=$1
            GROUP BY(format)
        ),
        lcc_runs AS (
            SELECT lcc.id, lcc.leftover, lcc.proof, lcc.format
            FROM leastcostchimps lcc
            JOIN lcc_mins mins
                ON mins.leftover=lcc.leftover
                AND mins.format=lcc.format
            WHERE lcc.map=$1
        )
        SELECT runs.*, rp.user_id
        FROM lcc_players rp JOIN lcc_runs runs ON rp.lcc_run=runs.id
        """,
        code,
    )
    if not len(payload):
        return []

    lccs = []
    run = payload[0][:4]
    players = []
    for i, row in enumerate(payload):
        if run[0] == row[0]:
            players.append(row[4])
        else:
            lccs.append(LCC(*run, players))
            run = row[:4]
            players = [row[4]]
    lccs.append(LCC(*run, players))
    return lccs


@postgres
async def get_completions_for(code, idx_start=0, amount=50, conn=None) -> list[ListCompletion]:
    payload = await conn.fetch(
        f"""
        WITH unique_runs AS (
            SELECT DISTINCT user_id, black_border, no_geraldo, current_lcc
            FROM list_completions
            WHERE map=$1
            ORDER BY current_lcc DESC,
                no_geraldo DESC,
                black_border DESC,
                user_id ASC
            LIMIT $3
            OFFSET $2
        )
        SELECT runs.*, lc.format
        FROM unique_runs runs JOIN list_completions lc ON runs.user_id = lc.user_id AND
            runs.black_border = lc.black_border AND
            runs.no_geraldo = lc.no_geraldo AND
            runs.current_lcc = lc.current_lcc
        WHERE map=$1
        ORDER BY runs.current_lcc DESC,
            runs.no_geraldo DESC,
            runs.black_border DESC,
            runs.user_id ASC
        """,
        code, idx_start, amount,
    )
    if not len(payload):
        return []

    completions = []
    run = payload[0][:4]
    formats = []
    for i, row in enumerate(payload):
        if list_eq(row[:4], run):
            formats.append(row[4])
        else:
            completions.append(ListCompletion(code, *run, formats))
            run = row[:4]
            formats = [row[4]]
    completions.append(ListCompletion(code, *run, formats))
    return completions


@postgres
async def map_exists(code, conn=None) -> bool:
    result = await conn.execute("SELECT code FROM maps WHERE code=$1", code)
    return int(result[len("SELECT "):]) > 0


@postgres
async def alias_exists(alias, conn=None) -> bool:
    result = await conn.execute("SELECT alias FROM map_aliases WHERE alias=$1", alias)
    return int(result[len("SELECT "):]) > 0
