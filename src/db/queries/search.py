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

    if "map" in entities and len(results) < limit:
        payload = await conn.fetch(
            """
            SELECT
                id, code, name, placement_curver, placement_allver, difficulty,
                r6_start, map_data, deleted_on, optimal_heros, map_preview_url,
                new_version, created_on
            FROM maps
            WHERE deleted_on IS NULL
                AND new_version IS NULL
                AND SIMILARITY(name, $1) > 0.1
            ORDER BY SIMILARITY(name, $1) DESC
            LIMIT $2
            """,
            query, limit - len(results)
        )
        results += [
            PartialMap(
                row["id"],
                row["code"],
                row["name"],
                row["placement_curver"],
                row["placement_allver"],
                row["difficulty"],
                row["r6_start"],
                row["map_data"],
                row["deleted_on"],
                row["optimal_heros"].split(";"),
                row["map_preview_url"],
                row["new_version"],
                row["created_on"],
            )
            for row in payload
        ]

    if "user" in entities and len(results) < limit:
        payload = await conn.fetch(
            """
            SELECT
                discord_id, name
            FROM users
            WHERE SIMILARITY(name, $1) > 0.1
            ORDER BY SIMILARITY(name, $1) DESC
            LIMIT $2
            """,
            query, limit - len(results)
        )
        results += [
            PartialUser(
                row["discord_id"],
                row["name"],
                None,
                True,
            )
            for row in payload
        ]

    return results
