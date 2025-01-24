import asyncpg.pool
import src.db.connection
from src.db.models import AchievementRole, DiscordRole
postgres = src.db.connection.postgres


@postgres
async def get_roles(
        conn: asyncpg.pool.PoolConnectionProxy = None,
) -> list[AchievementRole]:
    payload = await conn.fetch(
        """
        SELECT 
            ar.id,
            ar.lb_format,
            ar.lb_type,
            ar.threshold,
            ar.for_first,
            ar.tooltip_description,
            ar.name,
            ar.clr_border,
            ar.clr_inner,
            ARRAY_AGG((dr.guild_id, dr.role_id))
                OVER (PARTITION by ar.id) AS linked_roles
        FROM achievement_roles ar
        JOIN discord_role dr
            ON ar.id = dr.achievement_role_id
        """
    )

    return [
        AchievementRole(
            row["id"],
            row["lb_format"],
            row["lb_type"],
            row["threshold"],
            row["for_first"],
            row["tooltip_description"],
            row["name"],
            row["clr_border"],
            row["clr_inner"],
            [DiscordRole(
                row["linked_roles"][0],
                row["linked_roles"][1],
            )]
        )
        for row in payload
    ]
