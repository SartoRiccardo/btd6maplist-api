import asyncio
from src.utils.types import SearchEntity
import src.db.connection
from src.db.models import PartialMap, PartialUser
postgres = src.db.connection.postgres


@postgres
async def search(
        query: str,
        entities: list[SearchEntity],
        limit: int, conn=None
) -> list[PartialMap | PartialUser]:
    results = []

    if "map" in entities:
        payload = await conn.fetch(
            """
            SELECT
                m.code, m.name, mlm.placement_curver, mlm.placement_allver, mlm.difficulty,
                m.r6_start, m.map_data, mlm.optimal_heros, m.map_preview_url, mlm.botb_difficulty,
                mlm.remake_of,
                SIMILARITY(m.name, $1) AS simil
            FROM maps m
            JOIN latest_maps_meta(NOW()::timestamp) mlm
                ON m.code = mlm.code
            WHERE mlm.deleted_on IS NULL
                AND SIMILARITY(m.name, $1) > 0.1
            ORDER BY simil DESC
            LIMIT $2
            """,
            query, limit
        )
        results += [
            (
                row["simil"],
                PartialMap(
                    row["code"],
                    row["name"],
                    row["placement_curver"],
                    row["placement_allver"],
                    row["difficulty"],
                    row["botb_difficulty"],
                    row["remake_of"],
                    row["r6_start"],
                    row["map_data"],
                    None,
                    row["optimal_heros"].split(";"),
                    row["map_preview_url"],
                ),
            )
            for row in payload
        ]

    if "user" in entities:
        payload = await conn.fetch(
            """
            SELECT
                discord_id, name, is_banned,
                SIMILARITY(name, $1) AS simil
            FROM users
            WHERE SIMILARITY(name, $1) > 0.1
            ORDER BY simil DESC
            LIMIT $2
            """,
            query, limit
        )
        results += [
            (
                row["simil"],
                PartialUser(
                    row["discord_id"],
                    row["name"],
                    None,
                    True,
                    row["is_banned"],
                ),
            )
            for row in payload
        ]

    return sorted(results, key=lambda x: x[0], reverse=True)[:limit]
