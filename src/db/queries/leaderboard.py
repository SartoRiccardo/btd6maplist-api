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
        format: Literal["current", "all", "experts"] = True,
        conn=None,
) -> tuple[list[LeaderboardEntry], int]:
    lb_view = "list_curver_leaderboard"
    if format == "all":
        lb_view = "list_allver_leaderboard"
    elif format == "experts":
        lb_view = "experts_leaderboard"

    payload = await conn.fetch(
        f"""
        SELECT
            COUNT(*) OVER(),
            lb.score, lb.placement,
            u.discord_id, u.name
        FROM {lb_view} lb
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
        format: Literal["current", "all", "experts"] = True,
        conn=None
) -> tuple[list[LeaderboardEntry], int]:
    lb_view = "list_curver_lcclb"
    if format == "all":
        lb_view = "list_allver_lcclb"
    elif format == "experts":
        lb_view = "experts_lcc_leaderboard"

    payload = await conn.fetch(
        f"""
        SELECT
            COUNT(*) OVER(),
            lb.score, lb.placement,
            u.discord_id, u.name
        FROM {lb_view} lb
        JOIN users u
            ON u.discord_id = lb.user_id
        ORDER BY lb.placement
        """
    )
    return get_lb_list(payload)
