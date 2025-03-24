import src.db.connection
from src.db.models import Format
postgres = src.db.connection.postgres


@postgres
async def get_formats(
        conn: "asyncpg.pool.PoolConnectionProxy" = None
) -> list[Format]:
    payload = await conn.fetch(
        """
        SELECT 
            id, name, map_submission_wh, run_submission_wh, hidden, run_submission_status,
            map_submission_status, emoji
        FROM
            formats
        """
    )

    return [
        Format(
            row["id"],
            row["name"],
            row["map_submission_wh"],
            row["run_submission_wh"],
            row["hidden"],
            row["run_submission_status"],
            row["map_submission_status"],
            row["emoji"],
        )
        for row in payload
    ]


@postgres
async def get_format(
        format_id: int,
        conn: "asyncpg.pool.PoolConnectionProxy" = None
) -> Format | None:
    row = await conn.fetchrow(
        """
        SELECT 
            name, map_submission_wh, run_submission_wh, hidden, run_submission_status,
            map_submission_status, emoji
        FROM
            formats
        WHERE id = $1
        """,
        format_id,
    )

    return Format(
        format_id,
        row["name"],
        row["map_submission_wh"],
        row["run_submission_wh"],
        row["hidden"],
        row["run_submission_status"],
        row["map_submission_status"],
        row["emoji"],
    ) if row else None
