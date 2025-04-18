import src.db.connection
from src.db.models import LeaderboardEntry, PartialUser
from src.db.queries.subqueries import leaderboard_name, LeaderboardType
postgres = src.db.connection.postgres


def get_lb_list(payload) -> tuple[list[LeaderboardEntry], int]:
    if not len(payload):
        return [], 0

    return [
        LeaderboardEntry(
            PartialUser(row[3], row[4], None, False, False),
            float(row[1]),
            row[2]
        )
        for row in payload
    ], payload[0][0]


@postgres
async def get_leaderboard(
        idx_start: int = 0,
        amount: int = 50,
        format: int = 1,
        type: LeaderboardType = "points",
        conn=None,
) -> tuple[list[LeaderboardEntry], int]:
    payload = await conn.fetch(
        f"""
        SELECT
            COUNT(*) OVER(),
            lb.score, lb.placement,
            u.discord_id, u.name
        FROM {leaderboard_name(format, type)} lb
        JOIN users u
            ON u.discord_id = lb.user_id
        ORDER BY lb.placement
        LIMIT $1
        OFFSET $2
        """,
        amount, idx_start
    )
    return get_lb_list(payload)
