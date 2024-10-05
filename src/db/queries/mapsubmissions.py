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
        wh_data: str,
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
