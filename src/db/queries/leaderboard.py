import src.db.connection
from src.db.models import LeaderboardEntry, PartialUser
from typing import Literal
postgres = src.db.connection.postgres


def get_lb_list(payload) -> tuple[list[LeaderboardEntry], int]:
    if not len(payload):
        return [], 0

    return [
        LeaderboardEntry(
            PartialUser(row[3], row[4], None, False),
            float(row[1]),
            row[2]
        )
        for row in payload
    ], payload[0][0]


@postgres
async def get_maplist_leaderboard(
        idx_start: int = 0,
        amount: int = 50,
        format: int = 1,
        conn=None,
) -> tuple[list[LeaderboardEntry], int]:
    lb_views = {
        1: "list_curver_leaderboard",
        2: "list_allver_leaderboard",
        51: "experts_leaderboard",
    }

    payload = await conn.fetch(
        f"""
        SELECT
            COUNT(*) OVER(),
            lb.score, lb.placement,
            u.discord_id, u.name
        FROM {lb_views[format]} lb
        JOIN users u
            ON u.discord_id = lb.user_id
        ORDER BY lb.placement
        LIMIT $1
        OFFSET $2
        """,
        amount, idx_start
    )
    return get_lb_list(payload)


@postgres
async def get_maplist_lcc_leaderboard(
        format: int = 1,
        conn=None
) -> tuple[list[LeaderboardEntry], int]:
    lb_views = {
        1: "list_curver_lcclb",
        2: "list_allver_lcclb",
        51: "experts_lcc_leaderboard",
    }

    payload = await conn.fetch(
        f"""
        SELECT
            COUNT(*) OVER(),
            lb.score, lb.placement,
            u.discord_id, u.name
        FROM {lb_views[format]} lb
        JOIN users u
            ON u.discord_id = lb.user_id
        ORDER BY lb.placement
        """
    )
    return get_lb_list(payload)
