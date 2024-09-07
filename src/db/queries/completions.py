import src.db.connection
from src.db.models import ListCompletion, LCC, PartialUser
postgres = src.db.connection.postgres


@postgres
async def submit_run(
        map_code: str,
        black_border: bool,
        no_geraldo: bool,
        format_id: int,
        lcc_info: dict | None,  # leftover, proof
        player_id: int,
        conn=None,
) -> int | None:
    async with conn.transaction():
        lcc_id = None
        if lcc_info:
            lcc_id = await conn.fetchval(
                """
                INSERT INTO leastcostchimps(proof, leftover)
                VALUES($1, $2)
                RETURNING id
                """,
                lcc_info["proof"], lcc_info["leftover"]
            )
        run_id = await conn.fetchval(
            """
            INSERT INTO list_completions(map, black_border, no_geraldo, lcc, format)
            VALUES($1, $2, $3, $4, $5)
            RETURNING id
            """,
            map_code, black_border, no_geraldo, lcc_id, format_id
        )
        await conn.execute(
            """
            INSERT INTO listcomp_players(run, user_id)
            VALUES($1, $2)
            """,
            run_id, player_id
        )
        return run_id


@postgres
async def accept_run(run_id: int, conn=None) -> None:
    pass


@postgres
async def get_completion(run_id: str | int, conn=None) -> ListCompletion:
    if isinstance(run_id, str):
        run_id = int(run_id)

    payload = await conn.fetch(
        """
        WITH the_run AS (SELECT * FROM list_completions WHERE id=$1),
        runs_with_flags AS (
            SELECT r.*, (r.lcc = lccs.id AND lccs.id IS NOT NULL) AS current_lcc
            FROM the_run r
            LEFT JOIN lccs_by_map lccs
                ON lccs.id = r.lcc
        )
        SELECT
            run.map, run.black_border, run.no_geraldo, run.current_lcc, run.format, run.accepted,
            run.created_on, run.deleted_on,
            
            lcc.id, lcc.proof, lcc.leftover,
            ply.user_id, u.name
        FROM runs_with_flags run
        LEFT JOIN leastcostchimps lcc
            ON lcc.id = run.lcc
        LEFT JOIN listcomp_players ply
            ON ply.run = run.id
        LEFT JOIN users u
            ON ply.user_id = u.discord_id
        """,
        run_id
    )
    if len(payload):
        run_sidx = 0
        lcc_sidx = 8 + run_sidx
        ply_sidx = 3 + lcc_sidx

        run = payload[0]
        return ListCompletion(
            run_id,
            run[run_sidx],
            [PartialUser(row[ply_sidx], row[ply_sidx+1], None) for row in payload],
            run[run_sidx+1],
            run[run_sidx+2],
            run[run_sidx+3],
            run[run_sidx+4],
            LCC(run[lcc_sidx], run[lcc_sidx+1], run[lcc_sidx+2]) if run[lcc_sidx] else None,
            accepted=run[run_sidx+5],
            created_on=run[run_sidx+6],
            deleted_on=run[run_sidx+7],
        )
