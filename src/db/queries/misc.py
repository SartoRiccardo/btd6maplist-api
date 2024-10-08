import asyncio
from typing import Any
import src.db.connection
from src.db.models import ConfigVar
postgres = src.db.connection.postgres


@postgres
async def get_config(conn=None) -> list[ConfigVar]:
    payload = await conn.fetch("""
        SELECT name, value, type
        FROM config
    """)

    config = []
    for name, value, type in payload:
        try:
            if type.lower() == "int":
                config.append(ConfigVar(name, int(value)))
            elif type.lower() == "float":
                config.append(ConfigVar(name, float(value)))
            else:
                config.append(ConfigVar(name, value))
        except ValueError:
            config.append(ConfigVar(name, value))
    return config


@postgres
async def update_config(config: dict[str, Any], conn=None) -> None:
    for vname in config:
        await conn.execute(
            "UPDATE config SET value=$2 WHERE name=$1",
            vname, str(config[vname])
        )
