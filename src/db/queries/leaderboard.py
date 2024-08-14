import src.db.connection
from src.db.models import LeaderboardEntry
postgres = src.db.connection.postgres


@postgres
async def get_maplist_leaderboard(idx_start=0, amount=50, curver=True, conn=None):
    lb_view = "list_curver_leaderboard" if curver else "list_allver_leaderboard"
    payload = await conn.fetch(
        f"""
        SELECT
            lb1.*,
            (
                SELECT COUNT(*)+1
                FROM (
                    SELECT DISTINCT lb2.score
                    FROM {lb_view} lb2
                    WHERE lb2.score > lb1.score
                ) lb3
            ) AS placement
        FROM {lb_view} lb1
        LIMIT $1
        OFFSET $2
        """,
        amount, idx_start
    )
    return [
        LeaderboardEntry(row[0], float(row[1]), row[2])
        for row in payload
    ]
