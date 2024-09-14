import src.db.connection
from src.db.models import LeaderboardEntry, PartialUser
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
        idx_start=0,
        amount=50,
        curver=True,
        conn=None
) -> tuple[list[LeaderboardEntry], int]:
    lb_view = "list_curver_leaderboard" if curver else "list_allver_leaderboard"
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
        curver=True,
        conn=None
) -> tuple[list[LeaderboardEntry], int]:
    lb_view = "list_curver_lcclb" if curver else "list_allver_lcclb"
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
