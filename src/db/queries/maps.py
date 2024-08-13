import asyncio
import src.db.connection
from src.db.models import PartialListMap, PartialExpertMap, Map, LCC
postgres = src.db.connection.postgres


q_btd6_current_ver = "(SELECT value FROM config WHERE name='current_btd6_ver')::int"


@postgres
async def get_list_maps(conn=None, curver=True) -> list[PartialListMap]:
    q_is_verified = """
        SELECT (COUNT(*) > 0)
        FROM verifications
        WHERE map=code
            AND version=(SELECT value FROM config WHERE name='current_btd6_ver')::int
    """.strip()
    payload = await conn.fetch(f"""
        SELECT name, code, ({q_is_verified}) AS is_verified, placement_allver,
            placement_curver
        FROM maps
        WHERE $1 AND placement_curver > -1
            OR NOT $1 AND placement_allver > -1
    """, curver)
    return sorted([
        PartialListMap(row[0], row[1], row[3 + int(curver)], row[2])
        for row in payload
    ], key=lambda x: x.placement)


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
            AND version={q_btd6_current_ver}
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

    lcc, pl_codes, pl_creat, pl_verif, pl_compat = await asyncio.gather(
        get_lcc_for(code),
        conn.fetch("SELECT code, description FROM additional_codes WHERE belongs_to=$1", code),
        conn.fetch("SELECT user_id, role FROM creators WHERE map=$1", code),
        conn.fetch(f"""
            SELECT user_id, version
            FROM verifications WHERE map=$1
                AND (version={q_btd6_current_ver}
                OR version IS NULL)
        """, code),
        conn.fetch("SELECT status, version FROM mapver_compatibilities WHERE map=$1", code),
    )

    return Map(
        pl_map[0],
        pl_map[1],
        [(row[0], row[1]) for row in pl_creat],
        pl_codes,
        [(uid, ver/10 if ver else None) for uid, ver in pl_verif],
        pl_map[7],
        pl_map[2],
        pl_map[3],
        pl_map[4],
        lcc,
        pl_map[5],
        pl_map[6],
        pl_compat
    )


@postgres
async def get_lcc_for(code, conn=None) -> LCC | None:
    payload_runs = await conn.fetch("""
        SELECT id, leftover, proof
        FROM leastcostchimps
        WHERE map=$1
        ORDER BY leftover ASC
        LIMIT 1
    """, code)
    if len(payload_runs) == 0:
        return None
    the_run = payload_runs[0]
    payload_users = await conn.fetch("SELECT user_id FROM lcc_players WHERE lcc_run=$1", the_run[0])
    return LCC(
        the_run[0],
        the_run[1],
        the_run[2],
        [row[0] for row in payload_users]
    )
