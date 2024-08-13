import src.db.connection
from src.db.models import User
postgres = src.db.connection.postgres


@postgres
async def get_user(id, conn=None) -> User | None:
    payload = await conn.fetch("""
        SELECT name, nk_oak
        FROM users
        WHERE discord_id=$1
    """, int(id))
    if not len(payload):
        return None

    pl_user = payload[0]
    return User(
        int(id), pl_user[0], pl_user[1]
    )
