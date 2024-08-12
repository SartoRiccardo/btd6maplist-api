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
