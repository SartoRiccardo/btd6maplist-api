from datetime import datetime
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
                INSERT INTO leastcostchimps(leftover)
                VALUES($1)
                RETURNING id
                """,
                lcc_info["leftover"]
            )

        run_id = await conn.fetchval(
            """
            INSERT INTO completions
                (map, subm_notes)
            VALUES
                ($1, $2)
            RETURNING id
            """,
            map_code, notes,
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

        run_meta_id = await conn.fetchval(
            """
            INSERT INTO completions_meta
                (completion, black_border, no_geraldo, lcc, format)
            VALUES
                ($1, $2, $3, $4, $5)
            RETURNING id
            """,
            run_id, black_border, no_geraldo, lcc_id, format_id,
        )

        await conn.execute(
            """
            INSERT INTO comp_players(run, user_id)
            VALUES($1, $2)
            """,
            run_meta_id, player_id
        )

        return run_id


@postgres
async def get_completion(run_id: str | int, conn=None) -> ListCompletionWithMeta | None:
    if isinstance(run_id, str):
        run_id = int(run_id)

    run = await conn.fetchrow(
        """
        WITH the_run AS (
            SELECT
                c.id AS run_id,
                cm.id AS run_meta_id,
                c.*,
                cm.*
            FROM completions c
            JOIN completions_meta cm
                ON c.id = cm.completion
            WHERE c.id = $1
                AND cm.new_version IS NULL
        ),
        runs_with_flags AS (
            SELECT r.*, (r.lcc = lccs.id AND lccs.id IS NOT NULL) AS current_lcc
            FROM the_run r
            LEFT JOIN lccs_by_map lccs
                ON lccs.id = r.lcc
        )
        SELECT
            run.map, run.black_border, run.no_geraldo, run.current_lcc, run.format, run.accepted_by,
            run.submitted_on, run.deleted_on,
            ARRAY_AGG(cp.proof_url) FILTER (WHERE cp.proof_type = 0) OVER() AS subm_proof_img,
            ARRAY_AGG(cp.proof_url) FILTER (WHERE cp.proof_type = 1) OVER() AS subm_proof_vid,
            run.subm_notes, run.subm_wh_payload,
            
            lcc.id AS lcc_id, lcc.leftover,
            ARRAY_AGG(ply.user_id) OVER() AS user_ids,
            ARRAY_AGG(u.name) OVER() AS user_names
        FROM runs_with_flags run
        LEFT JOIN completion_proofs cp
            ON cp.run = run.run_id
        LEFT JOIN leastcostchimps lcc
            ON lcc.id = run.lcc
        LEFT JOIN comp_players ply
            ON ply.run = run.run_meta_id
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
            PartialUser(run["user_ids"][i], run["user_names"][i], None, False, False)
            for i in range(len(run["user_ids"]))
        ], preserve_order=False),
        run["black_border"],
        run["no_geraldo"],
        run["current_lcc"],
        run["format"],
        LCC(run["lcc_id"], run["leftover"]) if run["lcc_id"] else None,
        list_rm_dupe(run["subm_proof_img"]),
        list_rm_dupe(run["subm_proof_vid"]),
        run["subm_notes"],
        run["accepted_by"],
        run["submitted_on"],
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
        conn: asyncpg.pool.PoolConnectionProxy | None = None
) -> None:
    async with conn.transaction():
        await set_completion_meta(
            comp_id,
            black_border,
            no_geraldo,
            comp_format,
            lcc,
            user_ids,
            accept,
            conn=conn,
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
        conn: asyncpg.pool.PoolConnectionProxy | None = None
) -> None:
    async with conn.transaction():
        comp_id = await conn.fetchval(
            f"""
            INSERT INTO completions
                (map)
            VALUES ($1)
            RETURNING id
            """,
            map_code,
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

        await set_completion_meta(
            comp_id,
            black_border,
            no_geraldo,
            comp_format,
            lcc,
            user_ids,
            mod_id,
            conn=conn,
        )

        if comp_format == 1:
            await conn.execute("CALL set_comp_as_verification($1)", comp_id)

        return comp_id


@postgres
async def set_completion_meta(
        comp_id: int,
        black_border: bool,
        no_geraldo: bool,
        comp_format: int,
        lcc: dict | None,
        user_ids: list[int],
        mod_id: int | None,
        conn: asyncpg.pool.PoolConnectionProxy | None = None
) -> None:
    lcc_id = None
    if lcc:
        lcc_id = await conn.fetchval(
            """
            INSERT INTO leastcostchimps(leftover)
            VALUES($1)
            RETURNING id
            """,
            lcc["leftover"],
        )

    run_meta_id = await conn.fetchval(
        """
        INSERT INTO completions_meta
            (completion, black_border, no_geraldo, lcc, format, accepted_by)
        SELECT
            $1, $2, $3, $4, $5,
            COALESCE(cm.accepted_by, $6)
        FROM completions_meta cm
        WHERE cm.completion = $1
            AND cm.new_version IS NULL
            AND cm.deleted_on IS NULL
        
        UNION ALL
        
        SELECT
            $1::int, $2::bool, $3::bool, $4::int, $5::int, $6::bigint
            
        LIMIT 1
        RETURNING id
        """,
        comp_id, black_border, no_geraldo, lcc_id, comp_format, mod_id
    )

    await conn.executemany(
        """
        INSERT INTO comp_players
            (run, user_id)
        VALUES
            ($1, $2)
        """,
        [(run_meta_id, uid) for uid in user_ids]
    )

    await link_completions(conn=conn)


@postgres
async def link_completions(conn: asyncpg.pool.PoolConnectionProxy = None) -> None:
    await conn.execute(
        """
        UPDATE completions_meta cm_old
        SET
            new_version = cm_new.id
        FROM completions_meta cm_new
        WHERE cm_old.completion = cm_new.completion
            AND cm_old.created_on < cm_new.created_on
            AND cm_old.new_version IS NULL AND cm_new.new_version IS NULL
            AND cm_old.deleted_on IS NULL
        """
    )


@postgres
async def delete_completion(
        cid: int,
        hard_delete: bool = False,
        conn=None,
) -> None:
    if hard_delete:
        return await conn.execute(
            """
            DELETE FROM completions
            WHERE id = $1
            """,
            cid
        )

    await conn.execute(
        """
        INSERT INTO completions_meta
            (completion, black_border, no_geraldo, lcc, accepted_by, format, deleted_on)
        SELECT
            completion, black_border, no_geraldo, lcc, accepted_by, format, NOW()
        FROM completions_meta
        WHERE completion = $1
            AND deleted_on IS NULL
            AND new_version IS NULL
        """,
        cid
    )

    await link_completions(conn=conn)


@postgres
async def get_unapproved_completions(
        idx_start: int = 0,
        amount: int = 50,
        conn=None,
) -> tuple[list[ListCompletionWithMeta], int]:
    payload = await conn.fetch(
        """
        WITH unapproved_runs AS (
            SELECT
                c.id AS run_id,
                cm.id AS run_meta_id,
                cm.*,
                c.*,
                (cm.lcc IS NOT NULL) AS current_lcc
            FROM completions_meta cm
            JOIN completions c
                ON cm.completion = c.id
            WHERE cm.deleted_on IS NULL
                AND cm.accepted_by IS NULL
                AND cm.new_version IS NULL
        ),
        unique_runs AS (
            SELECT DISTINCT ON (run.run_id)

                run.map, run.black_border, run.no_geraldo, run.current_lcc, run.format, run.accepted_by,
                run.created_on AS comp_created_on, run.deleted_on AS comp_deleted_on,
                ARRAY_AGG(cp.proof_url) FILTER(WHERE cp.proof_type = 0) OVER(PARTITION BY run.run_id) AS subm_proof_img,
                ARRAY_AGG(cp.proof_url) FILTER(WHERE cp.proof_type = 1) OVER(PARTITION BY run.run_id) AS subm_proof_vid,
                run.subm_notes,
                run.run_id, run.subm_wh_payload,
                
                lcc.id AS lcc_id, lcc.leftover,
                ARRAY_AGG(ply.user_id) OVER(PARTITION BY run.run_meta_id) AS user_ids,
                
                m.name, mlm.placement_curver, mlm.placement_allver, mlm.difficulty, m.r6_start, 
                m.map_data, mlm.optimal_heros, m.map_preview_url, mlm.botb_difficulty, mlm.remake_of
            FROM unapproved_runs run
            LEFT JOIN leastcostchimps lcc
                ON lcc.id = run.lcc
            LEFT JOIN comp_players ply
                ON ply.run = run.run_meta_id
            LEFT JOIN completion_proofs cp
                ON cp.run = run.run_id
            JOIN maps m
                ON m.code = run.map
            JOIN map_list_meta mlm
                ON m.code = mlm.code
            WHERE mlm.deleted_on IS NULL
                AND mlm.new_version IS NULL
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
                run["map"],
                run["name"],
                run["placement_curver"],
                run["placement_allver"],
                run["difficulty"],
                run["botb_difficulty"],
                run["remake_of"],
                run["r6_start"],
                run["map_data"],
                None,
                run["optimal_heros"].split(";"),
                run["map_preview_url"],
            ),
            list_rm_dupe(run["user_ids"], preserve_order=False),
            run["black_border"],
            run["no_geraldo"],
            run["current_lcc"],
            run["format"],
            LCC(
                run["lcc_id"],
                run["leftover"],
            ) if run["lcc_id"] else None,
            list_rm_dupe(run["subm_proof_img"]),
            list_rm_dupe(run["subm_proof_vid"]),
            run["subm_notes"],
            run["accepted_by"],
            run["comp_created_on"],
            run["comp_deleted_on"],
            run["subm_wh_payload"],
        )
        for run in payload
    ]

    return completions, payload[0][0] if len(payload) else 0


@postgres
async def accept_completion(cid: int, who: int, conn: asyncpg.pool.PoolConnectionProxy = None) -> None:
    await conn.execute(
        """
        WITH new_entry AS (
            INSERT INTO completions_meta
                (completion, black_border, no_geraldo, lcc, accepted_by, format, copied_from_id)
            SELECT
                completion, black_border, no_geraldo, lcc, $2, format, id
            FROM completions_meta
            WHERE completion = $1
                AND deleted_on IS NULL
                AND new_version IS NULL
            RETURNING id AS new_id, copied_from_id AS old_id
        )
        INSERT INTO comp_players
            (run, user_id)
        SELECT
            cm.new_id, cp.user_id
        FROM new_entry cm
        JOIN comp_players cp
            ON cm.old_id = cp.run
        """,
        cid, who,
    )
    await link_completions(conn=conn)


@postgres
async def add_completion_wh_payload(run_id: int, payload: str | None, conn=None) -> None:
    await conn.execute(
        """
        UPDATE completions
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
            SELECT
                c.id AS run_id,
                r.id AS run_meta_id,
                c.*,
                r.*,
                (r.lcc = lccs.id AND lccs.id IS NOT NULL) AS current_lcc
            FROM completions_meta r
            JOIN completions c
                ON r.completion = c.id
            LEFT JOIN lccs_by_map lccs
                ON lccs.id = r.lcc
            WHERE r.deleted_on IS NULL
                AND r.new_version IS NULL
        ),
        accepted_runs AS (
            SELECT DISTINCT ON (run.run_id)
                run.run_id, run.map,
                ARRAY_AGG(ply.user_id) OVER(PARTITION BY run.run_meta_id) AS user_ids,
                run.black_border, run.no_geraldo, run.current_lcc, run.format,
                ARRAY_AGG(cp.proof_url) FILTER(WHERE cp.proof_type = 0) OVER(PARTITION BY run.run_id) AS subm_proof_img,
                ARRAY_AGG(cp.proof_url) FILTER(WHERE cp.proof_type = 1) OVER(PARTITION BY run.run_id) AS subm_proof_vid,
                run.subm_notes, run.accepted_by, run.created_on AS run_created_on, run.deleted_on AS run_deleted_on,
                
                lcc.id AS lcc_id, lcc.leftover,
                
                m.name, mlm.placement_curver, mlm.placement_allver, mlm.difficulty, m.r6_start,
                mlm.optimal_heros, m.map_preview_url, mlm.botb_difficulty, m.map_data, mlm.remake_of
            FROM runs_with_flags run
            LEFT JOIN leastcostchimps lcc
                ON lcc.id = run.lcc
            LEFT JOIN comp_players ply
                ON ply.run = run.run_meta_id
            LEFT JOIN completion_proofs cp
                ON cp.run = run.run_id
            JOIN map_list_meta mlm
                ON mlm.code = run.map
            JOIN maps m
                ON m.code = run.map
            WHERE run.accepted_by IS NOT NULL
                AND mlm.deleted_on IS NULL
                AND mlm.new_version IS NULL
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
            None if row["lcc_id"] is None else LCC(row["lcc_id"], row["leftover"]),
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
        transfer_formats: list[int] = None,
        conn=None
) -> None:
    if transfer_formats is None:
        transfer_formats = []
    now = datetime.now()
    args = [from_code, to_code, now]
    transfer_formats_filter = ""
    if None not in transfer_formats:
        args.append(transfer_formats)
        transfer_formats_filter = "AND cm.format = ANY($4::int[])"

    await conn.execute(
        f"""
        WITH copied_completions AS (
            INSERT INTO completions
                (map, submitted_on, subm_notes, subm_wh_payload, copied_from_id)
            SELECT
                $2, c.submitted_on, c.subm_notes, c.subm_wh_payload, c.id
            FROM completions c
            JOIN completions_meta cm
                ON c.id = cm.completion
            WHERE c.map = $1
                AND cm.deleted_on IS NULL
                AND cm.new_version IS NULL
                {transfer_formats_filter}
            RETURNING id AS new_id, copied_from_id AS old_id
        ),
        copied_completion_metas AS (
            INSERT INTO completions_meta
                (completion, black_border, no_geraldo, lcc, accepted_by, format, created_on, copied_from_id)
            SELECT 
                c.new_id, cm.black_border, cm.no_geraldo, cm.lcc, cm.accepted_by, cm.format, $3, cm.id
            FROM completions_meta cm
            JOIN copied_completions c
                ON cm.completion = c.old_id
            WHERE cm.deleted_on IS NULL
                AND cm.new_version IS NULL
                {transfer_formats_filter}
            RETURNING id AS new_id, copied_from_id AS old_id
        ),
        updated_completions AS (
            INSERT INTO completions_meta
                (completion, black_border, no_geraldo, lcc, accepted_by, format, created_on, deleted_on)
            SELECT 
                cm.completion, cm.black_border, cm.no_geraldo, cm.lcc, cm.accepted_by, cm.format, $3, $3
            FROM completions_meta cm
            JOIN copied_completion_metas ccm
                ON ccm.old_id = cm.id
                AND cm.new_version IS NULL
        )
        INSERT INTO comp_players
            (user_id, run)
        SELECT
            cp.user_id, ccm.new_id
        FROM comp_players cp
        JOIN copied_completion_metas ccm
            ON ccm.old_id = cp.run
        """,
        *args
    )

    await link_completions(conn=conn)
