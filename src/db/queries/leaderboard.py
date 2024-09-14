import src.db.connection
from src.db.models import LeaderboardEntry, PartialUser
postgres = src.db.connection.postgres


@postgres
async def get_maplist_leaderboard(idx_start=0, amount=50, curver=True, conn=None):
    lb_view = "list_curver_leaderboard" if curver else "list_allver_leaderboard"
    payload = await conn.fetch(
        f"""
        SELECT
            lb.score, lb.placement,
            u.discord_id, u.name
        FROM {lb_view} lb
        JOIN users u
            ON u.discord_id = lb.user_id
        LIMIT $1
        OFFSET $2
        """,
        amount, idx_start
    )
    return [
        LeaderboardEntry(
            PartialUser(row[2], row[3], None, False),
            float(row[0]),
            row[1]
        )
        for row in payload
    ]


@postgres
async def get_maplist_lcc_leaderboard(curver=True, conn=None):
    lb_view = "list_curver_lcclb" if curver else "list_allver_lcclb"
    payload = await conn.fetch(f"SELECT user_id, score, placement FROM {lb_view}")
    return [
        LeaderboardEntry(row[0], float(row[1]), row[2])
        for row in payload
    ]
