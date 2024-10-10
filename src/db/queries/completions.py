import asyncpg.pool
import src.db.connection
from src.db.models import ListCompletionWithMeta, LCC, PartialUser, PartialMap
from src.utils.misc import list_rm_dupe
postgres = src.db.connection.postgres


@postgres
async def submit_run(
        map_code: str,
        black_border: bool,
        no_geraldo: bool,
        format_id: int,
        lcc_info: dict | None,  # leftover, proof
        player_id: int,
        proof_img_url: list[str],
        proof_vid_url: list[str],
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
                (map, black_border, no_geraldo, lcc, format, subm_notes)
            VALUES
                ($1, $2, $3, $4, $5, $6)
            RETURNING id
            """,
            map_code, black_border, no_geraldo, lcc_id, format_id, notes,
        )

        proofs = [(run_id, url, 0) for url in proof_img_url] + \
            [(run_id, url, 1) for url in proof_vid_url]
        await conn.executemany(
            """
            INSERT INTO completion_proofs
                (run, proof_url, proof_type)
            VALUES ($1, $2, $3)
            """,
            proofs,
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
async def get_completion(run_id: str | int, conn=None) -> ListCompletionWithMeta | None:
    if isinstance(run_id, str):
        run_id = int(run_id)

    run = await conn.fetchrow(
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
            run.created_on, run.deleted_on,
            ARRAY_AGG(cp.proof_url) FILTER (WHERE cp.proof_type = 0) OVER() AS subm_proof_img,
            ARRAY_AGG(cp.proof_url) FILTER (WHERE cp.proof_type = 1) OVER() AS subm_proof_vid,
            run.subm_notes, run.subm_wh_payload,
            
            lcc.id AS lcc_id, lcc.proof, lcc.leftover,
            ARRAY_AGG(ply.user_id) OVER() AS user_ids,
            ARRAY_AGG(u.name) OVER() AS user_names
        FROM runs_with_flags run
        LEFT JOIN completion_proofs cp
            ON cp.run = run.id
        LEFT JOIN leastcostchimps lcc
            ON lcc.id = run.lcc
        LEFT JOIN listcomp_players ply
            ON ply.run = run.id
        LEFT JOIN users u
            ON ply.user_id = u.discord_id
        """,
        run_id
    )
    if run is None:
        return None

    return ListCompletionWithMeta(
        run_id,
        run["map"],
        list_rm_dupe([
            PartialUser(run["user_ids"][i], run["user_names"][i], None, False)
            for i in range(len(run["user_ids"]))
        ], preserve_order=False),
        run["black_border"],
        run["no_geraldo"],
        run["current_lcc"],
        run["format"],
        LCC(run["lcc_id"], run["proof"], run["leftover"]) if run["lcc_id"] else None,
        list_rm_dupe(run["subm_proof_img"]),
        list_rm_dupe(run["subm_proof_vid"]),
        run["subm_notes"],
        run["accepted_by"],
        run["created_on"],
        run["deleted_on"],
        run["subm_wh_payload"],
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

        other_params = []
        accept_params = ""
        if accept:
            accept_params = """
            accepted_by=$6,
            created_on=NOW(),
            """
            other_params = [accept]
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
        mod_id: int,
        subm_proof: str | None = None,
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
                (accepted_by, black_border, no_geraldo, format, lcc, map)
            VALUES ($6, $1, $2, $3, $4, $5)
            RETURNING id
            """,
            black_border,
            no_geraldo,
            comp_format,
            lcc_id,
            map_code,
            mod_id,
        )

        if subm_proof:
            await conn.execute(
                """
                INSERT INTO completion_proofs
                    (run, proof_url, proof_type)
                VALUES ($1, $2, 0)
                """,
                comp_id, subm_proof,
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
            await conn.execute("CALL dupe_comp_to_allver($1)", comp_id)
            await conn.execute("CALL set_comp_as_verification($1)", comp_id)


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
                run.created_on, run.deleted_on,
                ARRAY_AGG(cp.proof_url) FILTER(WHERE cp.proof_type = 0) OVER(PARTITION BY run.id) AS subm_proof_img,
                ARRAY_AGG(cp.proof_url) FILTER(WHERE cp.proof_type = 1) OVER(PARTITION BY run.id) AS subm_proof_vid,
                run.subm_notes,
                run.id AS run_id, run.subm_wh_payload,
                
                lcc.id AS lcc_id, lcc.proof, lcc.leftover,
                ARRAY_AGG(ply.user_id) OVER(PARTITION BY run.id) AS user_ids,
                
                m.id AS map_id, m.name, m.placement_curver, m.placement_allver, m.difficulty, m.r6_start, m.map_data,
                m.optimal_heros, m.map_preview_url, m.created_on, m.deleted_on, m.new_version
            FROM unapproved_runs run
            LEFT JOIN leastcostchimps lcc
                ON lcc.id = run.lcc
            LEFT JOIN listcomp_players ply
                ON ply.run = run.id
            LEFT JOIN completion_proofs cp
                ON cp.run = run.id
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

    completions = [
        ListCompletionWithMeta(
            run["run_id"],
            PartialMap(
                run["map_id"],
                run["map"],
                run["name"],
                run["placement_curver"],
                run["placement_allver"],
                run["difficulty"],
                run["r6_start"],
                "",
                run["deleted_on"],
                run["optimal_heros"].split(","),
                run["map_preview_url"],
                run["new_version"],
                run["created_on"],
            ),
            list_rm_dupe(run["user_ids"], preserve_order=False),
            run["black_border"],
            run["no_geraldo"],
            run["current_lcc"],
            run["format"],
            LCC(
                run["lcc_id"],
                run["proof"],
                run["leftover"],
            ) if run["lcc_id"] else None,
            list_rm_dupe(run["subm_proof_img"]),
            list_rm_dupe(run["subm_proof_vid"]),
            run["subm_notes"],
            run["accepted_by"],
            run["created_on"],
            run["deleted_on"],
            run["subm_wh_payload"],
        )
        for run in payload
    ]

    return completions, payload[0][0] if len(payload) else 0


@postgres
async def accept_completion(cid: int, who: int, conn=None) -> None:
    await conn.execute(
        """
        UPDATE list_completions
        SET accepted_by=$2
        WHERE id=$1
        """,
        cid, who,
    )


@postgres
async def add_completion_wh_payload(run_id: int, payload: str | None, conn=None) -> None:
    await conn.execute(
        """
        UPDATE list_completions
        SET subm_wh_payload=$2
        WHERE id=$1
        """,
        run_id, payload,
    )


@postgres
async def get_recent(limit: int = 5, formats: list[int] = None, conn=None) -> list[ListCompletionWithMeta]:
    additional_args = []

    format_filter = ""
    if formats is not None:
        additional_args.append(formats)
        format_filter = "AND run.format = ANY($2::int[])"

    payload = await conn.fetch(
        f"""
        WITH runs_with_flags AS (
            SELECT r.*, (r.lcc = lccs.id AND lccs.id IS NOT NULL) AS current_lcc
            FROM list_completions r
            LEFT JOIN lccs_by_map lccs
                ON lccs.id = r.lcc
        ),
        accepted_runs AS (
            SELECT DISTINCT ON (run.id)
                run.id AS run_id, run.map,
                ARRAY_AGG(ply.user_id) OVER(PARTITION BY run.id) AS user_ids,
                run.black_border, run.no_geraldo, run.current_lcc, run.format,
                ARRAY_AGG(cp.proof_url) FILTER(WHERE cp.proof_type = 0) OVER(PARTITION BY run.id) AS subm_proof_img,
                ARRAY_AGG(cp.proof_url) FILTER(WHERE cp.proof_type = 1) OVER(PARTITION BY run.id) AS subm_proof_vid,
                run.subm_notes, run.accepted_by, run.created_on AS run_created_on, run.deleted_on AS run_deleted_on,
                
                lcc.id AS lcc_id, lcc.proof, lcc.leftover,
                
                m.id AS map_id, m.name, m.placement_curver, m.placement_allver, m.difficulty, m.r6_start,
                m.optimal_heros, m.map_preview_url, m.created_on AS map_created_on
            FROM runs_with_flags run
            LEFT JOIN leastcostchimps lcc
                ON lcc.id = run.lcc
            LEFT JOIN listcomp_players ply
                ON ply.run = run.id
            LEFT JOIN completion_proofs cp
                ON cp.run = run.id
            JOIN maps m
                ON m.code = run.map
                AND m.deleted_on IS NULL
                AND m.new_version IS NULL
            WHERE run.deleted_on IS NULL
                AND run.accepted_by IS NOT NULL
                {format_filter}
        )
        SELECT *
        FROM accepted_runs
        ORDER BY run_created_on DESC
        LIMIT $1
        """,
        limit,
        *additional_args,
    )

    return [
        ListCompletionWithMeta(
            row["run_id"],
            PartialMap(
                row["map_id"],
                row["map"],
                row["name"],
                row["placement_curver"],
                row["placement_allver"],
                row["difficulty"],
                row["r6_start"],
                "",
                None,
                row["optimal_heros"].split(","),
                row["map_preview_url"],
                None,
                row["map_created_on"],
            ),
            list_rm_dupe(row["user_ids"], preserve_order=False),
            row["black_border"],
            row["no_geraldo"],
            row["current_lcc"],
            row["format"],
            None if row["lcc_id"] is None else LCC(row["lcc_id"], row["proof"], row["leftover"]),
            list_rm_dupe(row["subm_proof_img"]),
            list_rm_dupe(row["subm_proof_vid"]),
            row["subm_notes"],
            row["accepted_by"],
            row["run_created_on"],
            row["run_deleted_on"],
            None,
        )
        for row in payload
    ]


@postgres
async def transfer_all_completions(
        from_code: str,
        to_code: str,
        transfer_list_comps: bool = False,
        transfer_explist_comps: bool = False,
        conn=None
) -> None:
    if not transfer_list_comps and not transfer_explist_comps:
        return

    transfer_range = ""
    if transfer_explist_comps and not transfer_list_comps:
        transfer_range = "AND format BETWEEN 51 AND 100"
    elif not transfer_explist_comps and transfer_list_comps:
        transfer_range = "AND format BETWEEN 1 AND 50"

    await conn.execute(
        f"""
        UPDATE list_completions
        SET map=$2
        WHERE map=$1
            AND deleted_on IS NULL
            AND new_version IS NULL
            {transfer_range}
        """,
        from_code, to_code
    )