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
                m.r6_start, m.map_data, optimal_heros, map_preview_url, mlm.botb_difficulty,
                SIMILARITY(m.name, $1) AS simil
            FROM maps m
            JOIN map_list_meta mlm
                ON m.code = mlm.code
            WHERE mlm.deleted_on IS NULL
                AND mlm.new_version IS NULL
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
                    row["r6_start"],
                    row["map_data"],
                    None,
                    row["optimal_heros"].split(";"),
                    row["map_preview_url"],
                ),
            )
            for row in payload
        ]

    if "user" in entities and len(results) < limit:
        payload = await conn.fetch(
            """
            SELECT
                discord_id, name,
                SIMILARITY(name, $1) AS simil
            FROM users
            WHERE SIMILARITY(name, $1) > 0.1
            ORDER BY simil DESC
            LIMIT $2
            """,
            query, limit - len(results)
        )
        results += [
            (
                row["simil"],
                PartialUser(
                    row["discord_id"],
                    row["name"],
                    None,
                    True,
                ),
            )
            for row in payload
        ]

    return sorted(results, key=lambda x: x[0], reverse=True)[:limit]
