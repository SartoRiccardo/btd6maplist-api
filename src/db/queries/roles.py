import asyncio
import src.db.connection
from src.db.models import Role
postgres = src.db.connection.postgres


@postgres
async def get_roles(conn=None):
    payload = await conn.fetch(
        """
        SELECT
            DISTINCT ON (r.id)
            r.id, r.name, r.edit_maplist, r.edit_experts, r.requires_recording, r.cannot_submit,
            ARRAY_AGG(rg.role_can_grant) OVER(PARTITION BY r.id) AS can_grant
        FROM roles r
        LEFT JOIN role_grants rg
            ON r.id = rg.role_required
        """
    )

    return [
        Role(
            row["id"],
            row["name"],
            row["edit_maplist"],
            row["edit_experts"],
            row["requires_recording"],
            row["cannot_submit"],
            can_grant=[rl for rl in row["can_grant"] if rl is not None],
        )
        for row in payload
    ]
