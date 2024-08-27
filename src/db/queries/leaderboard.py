import src.db.connection
from src.db.models import LeaderboardEntry
postgres = src.db.connection.postgres


@postgres
async def get_maplist_leaderboard(idx_start=0, amount=50, curver=True, conn=None):
    lb_view = "list_curver_leaderboard" if curver else "list_allver_leaderboard"
    payload = await conn.fetch(
        f"""
        SELECT user_id, score, placement
        FROM {lb_view}
        LIMIT $1
        OFFSET $2
        """,
        amount, idx_start
    )
    return [
        LeaderboardEntry(row[0], float(row[1]), row[2])
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
