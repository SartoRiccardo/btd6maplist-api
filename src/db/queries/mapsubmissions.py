import asyncio
import src.db.connection
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
        completion_proof: str,
        edit: bool = False,
        conn=None,
) -> None:
    if isinstance(submitter, str):
        submitter = int(submitter)

    if edit:
        await conn.execute(
            """
            UPDATE map_submissions
            SET
                subm_notes=$2,
                format_id=$3,
                proposed=$4,
                completion_proof=$5,
                created_on=CURRENT_TIMESTAMP
            WHERE code=$1
            """,
            code, subm_notes, format_id, proposed, completion_proof,
        )
    else:
        await conn.execute(
            """
            INSERT INTO map_submissions
                (code, submitter, subm_notes, format_id, proposed, completion_proof)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            code, submitter, subm_notes, format_id, proposed, completion_proof,
        )


@postgres
async def add_map_submission_wh(
        code: str,
        wh_data: str | None,
        conn=None,
) -> None:
    await conn.execute(
        """
        UPDATE map_submissions
        SET wh_data=$2
        WHERE code=$1
        """,
        code, wh_data,
    )


@postgres
async def get_map_submission(
        code: str,
        format_id: int,
        not_deleted: bool = True,
        conn: "asyncpg.pool.PoolConnectionProxy" = None,
) -> MapSubmission | None:
    result = await get_map_submissions_on(
        code,
        [format_id],
        not_deleted=not_deleted,
        conn=conn,
    )
    return None if len(result) == 0 else result[0]


@postgres
async def get_map_submissions_on(
        code: str,
        format_ids: list[int],
        not_deleted: bool = True,
        conn: "asyncpg.pool.PoolConnectionProxy" = None,
) -> list[MapSubmission]:
    payload = await conn.fetch(
        f"""
        SELECT
            submitter, subm_notes, format_id, proposed, rejected_by,
            created_on, completion_proof, wh_data 
        FROM map_submissions
        WHERE code = $1
            AND format_id = ANY($2::int[])
            {"AND rejected_by IS NULL" if not_deleted else ""}
        ORDER BY created_on DESC
        """,
        code, format_ids
    )

    return [
        MapSubmission(
            code,
            row["submitter"],
            row["subm_notes"],
            row["format_id"],
            row["proposed"],
            row["rejected_by"],
            row["created_on"],
            row["completion_proof"],
            row["wh_data"],
        )
        for row in payload
    ]


@postgres
async def get_map_submissions(
        omit_rejected: bool = True,
        idx_start: int = 0,
        amount: int = 50,
        conn=None,
) -> tuple[int, list[MapSubmission]]:
    payload = await conn.fetch(
        f"""
        SELECT
            COUNT(*) OVER() AS total_count,
            ms.code, ms.submitter, ms.subm_notes, ms.format_id, ms.proposed,
            ms.rejected_by, ms.created_on, ms.completion_proof, ms.wh_data 
        FROM map_submissions ms
        LEFT JOIN map_list_meta m
            ON ms.code = m.code
            -- This should be done dynamically but it would require refactoring
            -- map_list_meta again to be (format_id INT FK, idx_value INT, new_version, created_on, deleted_on).
            AND (
                ms.format_id = 1 AND m.placement_curver IS NULL
                OR ms.format_id = 2 AND m.placement_allver IS NULL
                OR ms.format_id = 11 AND m.remake_of IS NULL
                OR ms.format_id = 51 AND m.difficulty IS NULL
                OR ms.format_id = 52 AND m.botb_difficulty IS NULL
            )
        WHERE m.code IS NULL
            AND m.deleted_on IS NULL
            AND m.new_version IS NULL
            {"AND ms.rejected_by IS NULL" if omit_rejected else ""}
        ORDER BY ms.created_on DESC
        LIMIT $1
        OFFSET $2
        """,
        amount, idx_start
    )
    submissions = [
        MapSubmission(
            row["code"],
            row["submitter"],
            row["subm_notes"],
            row["format_id"],
            row["proposed"],
            row["rejected_by"],
            row["created_on"],
            row["completion_proof"],
            row["wh_data"],
        ) for row in payload
    ]

    return 0 if not len(payload) else payload[0]["total_count"], submissions


@postgres
async def reject_submission(
        code: str,
        format_id: str | int,
        rejected_by: str | int,
        conn=None,
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
