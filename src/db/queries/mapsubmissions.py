import asyncio
import src.db.connection
from src.utils.formats.formats import format_keys
from src.db.models import (
    MapSubmission,
)
postgres = src.db.connection.postgres


@postgres
async def add_map_submission(
        code: str,
        submitter: str | int,
        subm_notes: str | None,
        format_id: int,
        proposed: int,
        completion_proof: str | None,
        edit: bool = False,
        conn=None,
) -> int:
    if isinstance(submitter, str):
        submitter = int(submitter)

    if edit:
        return await conn.fetchval(
            """
            UPDATE map_submissions
            SET
                subm_notes=$2,
                format_id=$3,
                proposed=$4,
                completion_proof=$5,
                created_on=CURRENT_TIMESTAMP
            WHERE code=$1
            RETURNING id
            """,
            code, subm_notes, format_id, proposed, completion_proof,
        )
    else:
        return await conn.fetchval(
            """
            INSERT INTO map_submissions
                (code, submitter, subm_notes, format_id, proposed, completion_proof)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
            """,
            code, submitter, subm_notes, format_id, proposed, completion_proof,
        )


@postgres
async def set_map_submission_wh(
        submission_id: int | str,
        wh_msg_id: int | str | None,
        wh_data: str | None,
        conn: "asyncpg.pool.PoolConnectionProxy" = None,
) -> None:
    if isinstance(submission_id, str):
        submission_id = int(submission_id)
    if isinstance(wh_msg_id, str):
        wh_msg_id = int(wh_msg_id)

    await conn.execute(
        """
        UPDATE map_submissions
        SET
            wh_data = $2,
            wh_msg_id = $3
        WHERE id = $1
        """,
        submission_id, wh_data, wh_msg_id
    )


@postgres
async def get_map_submission(
        code: str,
        format_id: int | str,
        not_deleted: bool = True,
        conn: "asyncpg.pool.PoolConnectionProxy" = None,
) -> MapSubmission | None:
    if isinstance(format_id, str):
        format_id = int(format_id)

    _total, result = await get_map_submissions(
        on_code=code,
        on_formats=[format_id],
        omit_rejected=not_deleted,
        conn=conn,
    )
    return None if len(result) == 0 else result[0]


@postgres
async def get_map_submissions(
        omit_rejected: bool = True,
        idx_start: int = 0,
        amount: int = 50,
        on_code: str = None,
        on_formats: list[int] = None,
        conn: "asyncpg.pool.PoolConnectionProxy" = None,
) -> tuple[int, list[MapSubmission]]:
    join_clause = " OR ".join([
        f"ms.format_id = {format_id} AND m.{format_keys[format_id]} IS NOT NULL"
        for format_id in format_keys
    ])

    args = [amount, idx_start]
    pg_idx = 3

    filter_code = ""
    if on_code is not None:
        args.append(on_code)
        filter_code = f"AND ms.code = ${pg_idx}"
        pg_idx += 1

    filter_formats = ""
    if on_formats is not None:
        args.append(on_formats)
        filter_formats = f"AND ms.format_id = ANY(${pg_idx}::int[])"
        pg_idx += 1

    payload = await conn.fetch(
        f"""
        SELECT
            COUNT(*) OVER() AS total_count,
            ms.code, ms.submitter, ms.subm_notes, ms.format_id, ms.proposed,
            ms.rejected_by, ms.created_on, ms.completion_proof, ms.wh_data, ms.wh_msg_id, 
            ms.id
        FROM map_submissions ms
        LEFT JOIN map_list_meta m
            ON ms.code = m.code
            AND m.created_on > ms.created_on
            -- This should be done dynamically but it would require refactoring
            -- map_list_meta again to be (format_id INT FK, idx_value INT, new_version, created_on, deleted_on).
            AND ({join_clause})
        WHERE m.code IS NULL
            {"AND ms.rejected_by IS NULL" if omit_rejected else ""}
            {filter_code}
            {filter_formats}
        ORDER BY ms.created_on DESC
        LIMIT $1
        OFFSET $2
        """,
        *args,
    )
    submissions = [
        MapSubmission(
            row["id"],
            row["code"],
            row["submitter"],
            row["subm_notes"],
            row["format_id"],
            row["proposed"],
            row["rejected_by"],
            row["created_on"],
            row["completion_proof"],
            row["wh_data"],
            row["wh_msg_id"],
        ) for row in payload
    ]

    return 0 if not len(payload) else payload[0]["total_count"], submissions


@postgres
async def reject_submission(
        code: str,
        format_id: str | int,
        rejected_by: str | int,
        conn: "asyncpg.pool.PoolConnectionProxy" = None,
) -> None:
    if isinstance(rejected_by, str):
        rejected_by = int(rejected_by)
    if isinstance(format_id, str):
        format_id = int(format_id)

    await conn.execute(
        """
        UPDATE map_submissions
        SET rejected_by = $3
        WHERE code = $1
            AND format_id = $2
        """,
        code, format_id, rejected_by,
    )


@postgres
async def get_map_submissions_by_message(
        message_id: str | int,
        conn: "asyncpg.pool.PoolConnectionProxy" = None,
) -> MapSubmission | None:
    if isinstance(message_id, str):
        message_id = int(message_id)
    submission = await conn.fetchrow(
        """
        SELECT
            ms.code, ms.submitter, ms.subm_notes, ms.format_id, ms.proposed,
            ms.rejected_by, ms.created_on, ms.completion_proof, ms.wh_data,
            ms.wh_msg_id, ms.id
        FROM map_submissions ms
        WHERE ms.wh_msg_id = $1
        """,
        message_id
    )

    return None if submission is None else MapSubmission(
        submission["id"],
        submission["code"],
        submission["submitter"],
        submission["subm_notes"],
        submission["format_id"],
        submission["proposed"],
        submission["rejected_by"],
        submission["created_on"],
        submission["completion_proof"],
        submission["wh_data"],
        submission["wh_msg_id"],
    )
