import asyncpg.pool
import src.db.connection
from src.db.models import ListCompletionWithMeta, LCC, PartialUser, PartialMap
postgres = src.db.connection.postgres


@postgres
async def submit_run(
        map_code: str,
        black_border: bool,
        no_geraldo: bool,
        format_id: int,
        lcc_info: dict | None,  # leftover, proof
        player_id: int,
        proof_url: str | None,
        proof_vid_url: str | None,
        notes: str | None,
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
            INSERT INTO list_completions
                (map, black_border, no_geraldo, lcc, format, subm_proof_img, subm_proof_vid,
                subm_notes)
            VALUES
                ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id
            """,
            map_code, black_border, no_geraldo, lcc_id, format_id, proof_url, proof_vid_url, notes,
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
async def get_completion(run_id: str | int, conn=None) -> ListCompletionWithMeta:
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
            run.map, run.black_border, run.no_geraldo, run.current_lcc, run.format, run.accepted_by,
            run.created_on, run.deleted_on, run.subm_proof_img, run.subm_proof_vid, run.subm_notes,
            
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
        lcc_sidx = 11 + run_sidx
        ply_sidx = 3 + lcc_sidx

        run = payload[0]
        return ListCompletionWithMeta(
            run_id,
            run[run_sidx],
            [PartialUser(row[ply_sidx], row[ply_sidx+1], None, False) for row in payload],
            run[run_sidx+1],
            run[run_sidx+2],
            run[run_sidx+3],
            run[run_sidx+4],
            LCC(run[lcc_sidx], run[lcc_sidx+1], run[lcc_sidx+2]) if run[lcc_sidx] else None,
            run[run_sidx+8],
            run[run_sidx+9],
            run[run_sidx+10],
            run[run_sidx+5],
            run[run_sidx+6],
            run[run_sidx+7],
        )


@postgres
async def edit_completion(
        comp_id: int,
        black_border: bool,
        no_geraldo: bool,
        comp_format: int,
        lcc: dict | None,
        user_ids: list[int],
        accept: int | None = None,
        conn: asyncpg.pool.Pool | None = None
) -> None:
    async with conn.transaction():
        lcc_id = None
        await conn.execute(
            """
            DELETE FROM leastcostchimps lcc
            USING list_completions runs
            WHERE lcc.id = runs.lcc
                AND runs.id = $1
            """,
            comp_id
        )
        if lcc:
            lcc_id = await conn.fetchval(
                """
                INSERT INTO leastcostchimps(proof, leftover)
                VALUES($1, $2)
                RETURNING id
                """,
                lcc["proof"], lcc["leftover"],
            )

        await conn.execute(
            """
            DELETE FROM listcomp_players ply
            WHERE ply.run=$1
            """,
            comp_id
        )
        await conn.executemany(
            """
            INSERT INTO listcomp_players(run, user_id)
            VALUES($1, $2)
            """,
            [(comp_id, uid) for uid in user_ids]
        )

        other_params = [accept]
        accept_params = ""
        if accept:
            accept_params = """
            accepted_by=$6,
            created_on=NOW(),
            """
        await conn.execute(
            f"""
            UPDATE list_completions
            SET
                {accept_params}
                black_border=$2,
                no_geraldo=$3,
                format=$4,
                lcc=$5
            WHERE id=$1
            """,
            comp_id,
            black_border,
            no_geraldo,
            comp_format,
            lcc_id,
            *other_params,
        )


@postgres
async def add_completion(
        map_code: str,
        black_border: bool,
        no_geraldo: bool,
        comp_format: int,
        lcc: dict | None,
        user_ids: list[int],
        conn: asyncpg.pool.Pool | None = None
) -> None:
    async with conn.transaction():
        lcc_id = None
        if lcc:
            lcc_id = await conn.fetchval(
                """
                INSERT INTO leastcostchimps(proof, leftover)
                VALUES($1, $2)
                RETURNING id
                """,
                lcc["proof"], lcc["leftover"],
            )

        comp_id = await conn.fetchval(
            f"""
            INSERT INTO list_completions
                (accepted, black_border, no_geraldo, format, lcc, map)
            VALUES (TRUE, $1, $2, $3, $4, $5)
            RETURNING id
            """,
            black_border,
            no_geraldo,
            comp_format,
            lcc_id,
            map_code,
        )

        await conn.executemany(
            """
            INSERT INTO listcomp_players(run, user_id)
            VALUES($1, $2)
            ON CONFLICT DO NOTHING
            """,
            [(comp_id, uid) for uid in user_ids]
        )

        if comp_format == 1:
            await conn.execute(
                """
                CALL dupe_comp_to_allver($1)
                """,
                comp_id
            )


@postgres
async def delete_completion(
        cid: int,
        hard_delete: bool = False,
        conn=None,
) -> None:
    q = ("""
        DELETE FROM list_completions
        WHERE id=$1
        """) if hard_delete else ("""
        UPDATE list_completions
        SET deleted_on=NOW()
        WHERE id=$1
        """)

    await conn.execute(q, cid)


@postgres
async def get_unapproved_completions(
        idx_start: int = 0,
        amount: int = 50,
        conn=None,
) -> tuple[list[ListCompletionWithMeta], int]:
    payload = await conn.fetch(
        """
        WITH unapproved_runs AS (
            SELECT r.*, (r.lcc IS NOT NULL) AS current_lcc
            FROM list_completions r
            WHERE r.deleted_on IS NULL
                AND r.accepted_by IS NULL
        ),
        unique_runs AS (
            SELECT DISTINCT ON (run.id)

                run.map, run.black_border, run.no_geraldo, run.current_lcc, run.format, run.accepted_by,
                run.created_on, run.deleted_on, run.subm_proof_img, run.subm_proof_vid, run.subm_notes,
                run.id,
                
                lcc.id, lcc.proof, lcc.leftover,
                ARRAY_AGG(ply.user_id) OVER(PARTITION BY run.id) AS user_id,
                
                m.id, m.name, m.placement_curver, m.placement_allver, m.difficulty, m.r6_start, m.map_data,
                m.optimal_heros, m.map_preview_url, m.created_on, m.deleted_on, m.new_version
            FROM unapproved_runs run
            LEFT JOIN leastcostchimps lcc
                ON lcc.id = run.lcc
            LEFT JOIN listcomp_players ply
                ON ply.run = run.id
            JOIN maps m
                ON m.code = run.map
            WHERE m.deleted_on IS NULL
                AND m.new_version IS NULL
        )
        SELECT 
            COUNT(*) OVER() AS total_count, uq.*
        FROM unique_runs uq
        ORDER BY uq.map
        LIMIT $2
        OFFSET $1
        """,
        idx_start,
        amount
    )

    run_sidx = 1
    lcc_sidx = 12 + run_sidx
    ply_sidx = 3 + lcc_sidx
    map_sidx = 1 + ply_sidx

    completions = [
        ListCompletionWithMeta(
            run[run_sidx + 11],
            PartialMap(
                run[map_sidx],
                run[run_sidx],
                run[map_sidx + 1],
                run[map_sidx + 2],
                run[map_sidx + 3],
                run[map_sidx + 4],
                run[map_sidx + 5],
                run[map_sidx + 6],
                run[map_sidx + 10],
                run[map_sidx + 7].split(","),
                run[map_sidx + 8],
                run[map_sidx + 11],
                run[map_sidx + 9],
            ),
            run[ply_sidx],
            run[run_sidx + 1],
            run[run_sidx + 2],
            run[run_sidx + 3],
            run[run_sidx + 4],
            LCC(
                run[lcc_sidx],
                run[lcc_sidx + 1],
                run[lcc_sidx + 2]
            ) if run[lcc_sidx] else None,
            run[run_sidx + 8],
            run[run_sidx + 9],
            run[run_sidx + 10],
            run[run_sidx + 5],
            run[run_sidx + 6],
            run[run_sidx + 7],
        )
        for run in payload
    ]

    return completions, payload[0][0] if len(payload) else 0
