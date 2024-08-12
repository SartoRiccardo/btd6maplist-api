import src.db.connection
from src.db.models import PartialListMap
postgres = src.db.connection.postgres


@postgres
async def list_maps(conn=None, curver=True) -> list[PartialListMap]:
    payload = await conn.fetch("""
        SELECT name, code, placement_allver, placement_curver
        FROM maps
        WHERE $1 AND placement_curver > -1
            OR NOT $1 AND placement_allver > -1
    """, curver)
    return sorted([
        PartialListMap(row[0], row[1], row[2 + int(curver)])
        for row in payload
    ], key=lambda x: x.placement)
