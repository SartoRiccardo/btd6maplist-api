import src.db.connection
from src.db.models import LeaderboardEntry
postgres = src.db.connection.postgres


q_lb_format = """
SELECT
    lb1.*,
    (
        SELECT COUNT(*)+1
        FROM (
            SELECT lb2.score
            FROM {0} lb2
            WHERE lb2.score > lb1.score
        ) lb3
    ) AS placement
FROM {0} lb1
"""


@postgres
async def get_maplist_leaderboard(idx_start=0, amount=50, curver=True, conn=None):
    lb_view = "list_curver_leaderboard" if curver else "list_allver_leaderboard"
    payload = await conn.fetch(
        f"""
        {q_lb_format.format(lb_view)}
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
    payload = await conn.fetch(
        q_lb_format.format(lb_view)
    )
    return [
        LeaderboardEntry(row[0], float(row[1]), row[2])
        for row in payload
    ]
