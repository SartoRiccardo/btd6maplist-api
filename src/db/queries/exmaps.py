import src.db.connection
from src.db.models import PartialExpertMap
postgres = src.db.connection.postgres


@postgres
async def list_maps(conn=None) -> list[PartialExpertMap]:
    payload = await conn.fetch("""
        SELECT name, code, difficulty
        FROM maps
        WHERE difficulty > -1
    """)
    return [
        PartialExpertMap(row[0], row[1], row[2])
        for row in payload
    ]
