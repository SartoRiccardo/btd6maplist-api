import asyncpg.pool
from typing import Generator
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
            ar.lb_format,
            ar.lb_type,
            ar.threshold,
            ar.for_first,
            ar.tooltip_description,
            ar.name,
            ar.clr_border,
            ar.clr_inner,
            ARRAY_AGG((dr.guild_id, dr.role_id))
                OVER (PARTITION by (dr.ar_lb_format, dr.ar_lb_type, dr.ar_threshold)) AS linked_roles
        FROM achievement_roles ar
        LEFT JOIN discord_roles dr
            ON ar.lb_format = dr.ar_lb_format
            AND ar.lb_type = dr.ar_lb_type
            AND ar.threshold = dr.ar_threshold
        """
    )

    return [
        AchievementRole(
            row["lb_format"],
            row["lb_type"],
            row["threshold"],
            row["for_first"],
            row["tooltip_description"],
            row["name"],
            row["clr_border"],
            row["clr_inner"],
            [
                DiscordRole(gid, rid)
                for gid, rid in row["linked_roles"]
                if gid is not None and rid is not None
            ],
        )
        for row in payload
    ]


@postgres
async def get_duplicate_ds_roles(
        lb_format: int,
        lb_type: str,
        role_list: list[int],
        conn: asyncpg.pool.PoolConnectionProxy = None,
) -> list[int]:
    payload = await conn.fetch(
        """
        SELECT
            role_id
        FROM discord_roles
        WHERE ar_lb_format != $1
            AND ar_lb_type != $2
            AND NOT role_id = ANY($3::bigint[])
        """,
        lb_format, lb_type, role_list,
    )
    return [r["role_id"] for r in payload]


@postgres
async def update_ach_roles(
        lb_format: int,
        lb_type: str,
        role_list: list[dict],
        conn: asyncpg.pool.PoolConnectionProxy = None,
) -> None:
    def generate_discord_role_list() -> Generator[tuple[int, str, int, str, str], None, None]:
        for r in role_list:
            for dr in r["linked_roles"]:
                yield lb_format, lb_type, r["threshold"], dr["guild_id"], dr["role_id"]

    async with conn.transaction():
        await conn.execute(
            """
            CREATE TEMP TABLE tmp_achievement_roles (
                lb_format INT,
                lb_type VARCHAR(16),
                threshold INT,
                for_first BOOLEAN,
                tooltip_description VARCHAR(128),
                name VARCHAR(32),
                clr_border INT,
                clr_inner INT
            ) ON COMMIT DROP;
            
            CREATE TEMP TABLE tmp_discord_roles (
                ar_lb_format INT NOT NULL,
                ar_lb_type VARCHAR(16) NOT NULL,
                ar_threshold INT NOT NULL DEFAULT 0,
                guild_id BIGINT NOT NULL,
                role_id BIGINT NOT NULL PRIMARY KEY
            ) ON COMMIT DROP;
            """
        )
        await conn.executemany(
            """
            INSERT INTO tmp_achievement_roles
                (lb_format, lb_type, threshold, for_first, tooltip_description, name, clr_border, clr_inner)
            VALUES
                ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            [(
                lb_format, lb_type, r["threshold"], r["for_first"], r["tooltip_description"], r["name"],
                r["clr_border"], r["clr_inner"],
            ) for r in role_list],
        )
        await conn.executemany(
            """
            INSERT INTO tmp_discord_roles
                (ar_lb_format, ar_lb_type, ar_threshold, guild_id, role_id)
            VALUES
                ($1, $2, $3, $4, $5)
            """,
            [data for data in generate_discord_role_list()]
        )
        await conn.execute(
            """
            DELETE FROM achievement_roles
            WHERE (lb_format, lb_type, threshold) NOT IN (
                SELECT
                    lb_format, lb_type, threshold
                FROM tmp_achievement_roles
            )
            AND lb_format = $1
            AND lb_type = $2
            """,
            lb_format, lb_type
        )
        await conn.execute(
            """
            UPDATE achievement_roles ar
            SET for_first = tar.for_first,
                tooltip_description = tar.tooltip_description,
                name = tar.name,
                clr_border = tar.clr_border,
                clr_inner = tar.clr_inner
            FROM tmp_achievement_roles tar
            WHERE ar.lb_format = tar.lb_format
                AND ar.lb_type = tar.lb_type
                AND ar.threshold = tar.threshold;

            INSERT INTO achievement_roles
                (lb_format, lb_type, threshold, for_first, tooltip_description, name, clr_border, clr_inner)
            SELECT
                lb_format, lb_type, threshold, for_first, tooltip_description, name, clr_border, clr_inner
            FROM tmp_achievement_roles
            WHERE (lb_format, lb_type, threshold) NOT IN (
                SELECT
                    lb_format, lb_type, threshold
                FROM achievement_roles
            );
            """,
        )

        # TODO Modify linked roles
