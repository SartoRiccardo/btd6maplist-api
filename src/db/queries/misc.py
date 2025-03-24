import asyncio
from typing import Any
import src.db.connection
postgres = src.db.connection.postgres


ConfigVars = dict[str, int | float | str]


def typecast_config(payload: list[tuple[str, str, str]]) -> ConfigVars:
    config = {}
    for name, value, type in payload:
        try:
            if type.lower() == "int":
                config[name] = int(value)
            elif type.lower() == "float":
                config[name] = float(value)
            else:
                config[name] = value
        except ValueError:
            config[name] = value
    return config


@postgres
async def get_config(conn: "asyncpg.pool.PoolConnectionProxy" = None) -> ConfigVars:
    payload = await conn.fetch("""
        SELECT name, value, type
        FROM config
    """)

    return typecast_config(payload)


@postgres
async def update_config(
        config: dict[str, Any],
        formats_to_edit: list[str | None],
        conn: "asyncpg.pool.PoolConnectionProxy" = None
) -> ConfigVars:
    async with conn.transaction():
        await conn.execute(
            """
            CREATE TEMP TABLE new_config (
                name VARCHAR(255),
                value VARCHAR(255)
            ) ON COMMIT DROP
            """
        )

        await conn.executemany(
            """
            INSERT INTO new_config
                (name, value)
            VALUES ($1, $2)
            """,
            [(name, str(config[name])) for name in config]
        )

        args = []
        format_filter = ""
        if None not in formats_to_edit:
            args.append(formats_to_edit)
            format_filter = "AND cf.format_id = ANY($1::int[])"
        payload = await conn.fetch(
            f"""
            UPDATE config c
            SET
                value = nc.value
            FROM config_formats cf
            JOIN new_config nc
                ON cf.config_name = nc.name
            WHERE c.name = nc.name
                {format_filter}
            RETURNING c.name, c.value, c.type
            """,
            *args
        )

        return typecast_config(payload)
