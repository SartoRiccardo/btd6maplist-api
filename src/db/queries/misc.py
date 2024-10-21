import asyncio
from typing import Any
import src.db.connection
from src.db.models import ConfigVar
postgres = src.db.connection.postgres


@postgres
async def get_config(conn=None) -> dict[str, int | float | str]:
    payload = await conn.fetch("""
        SELECT name, value, type
        FROM config
    """)

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
async def update_config(config: dict[str, Any], conn=None) -> None:
    for vname in config:
        await conn.execute(
            "UPDATE config SET value=$2 WHERE name=$1",
            vname, str(config[vname])
        )
