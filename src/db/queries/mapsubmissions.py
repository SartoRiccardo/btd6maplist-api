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
        for_list: int,
        proposed: int,
        completion_proof: str,
        conn=None,
) -> None:
    if isinstance(submitter, str):
        submitter = int(submitter)
    await conn.execute(
        """
        INSERT INTO map_submissions
            (code, submitter, subm_notes, for_list, proposed, completion_proof)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        code, submitter, subm_notes, for_list, proposed, completion_proof,
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
        conn=None,
) -> MapSubmission | None:
    payload = await conn.fetchrow(
        """
        SELECT
            submitter, subm_notes, for_list, proposed, rejected_by,
            created_on, completion_proof, wh_data 
        FROM map_submissions
        WHERE code=$1
        """,
        code,
    )
    return MapSubmission(
        code,
        payload["submitter"],
        payload["subm_notes"],
        payload["for_list"],
        payload["proposed"],
        payload["rejected_by"],
        payload["created_on"],
        payload["completion_proof"],
        payload["wh_data"],
    ) if payload else None


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
            ms.code, ms.submitter, ms.subm_notes, ms.for_list, ms.proposed,
            ms.rejected_by, ms.created_on, ms.completion_proof, ms.wh_data 
        FROM map_submissions ms
        LEFT JOIN maps m
            on ms.code = m.code
        WHERE m.code IS NULL
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
            row["for_list"],
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
        rejector: str | int,
        conn=None,
) -> None:
    if isinstance(rejector, str):
        rejector = int(rejector)

    await conn.execute(
        """
        UPDATE map_submissions
        SET rejected_by=$2
        WHERE code=$1
        """,
        code, rejector,
    )
