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
        FROM formats
        ORDER BY id ASC
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
        format_id: int | str,
        conn: "asyncpg.pool.PoolConnectionProxy" = None
) -> Format | None:
    if isinstance(format_id, str) and format_id.isnumeric():
        format_id = int(format_id)
    if not isinstance(format_id, int):
        return None

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


@postgres
async def edit_format(
        format_id: int,
        hidden: bool,
        run_submission_status: int,
        map_submission_status: int,
        map_submission_wh: str | None = None,
        run_submission_wh: str | None = None,
        emoji: str | None = None,
        conn: "asyncpg.pool.PoolConnectionProxy" = None,
) -> None:
    args = [hidden, run_submission_status, map_submission_status, map_submission_wh, run_submission_wh]
    updates = []

    if emoji:
        args.append(emoji)
        updates.append("emoji")

    await conn.execute(
        f"""
        UPDATE formats
        SET
            {"".join([
                var_name + " = $" + str(i+7) + ","
                for i, var_name in enumerate(updates)
            ])}
            hidden = $2,
            run_submission_status = $3,
            map_submission_status = $4,
            map_submission_wh = $5,
            run_submission_wh = $6
        WHERE id = $1
        """,
        format_id, *args
    )
