import src.db.connection
import re
from src.requests.DiscordRequestsMock import DiscordRequestsMock


perms = {
    DiscordRequestsMock.ADMIN: [4, 5],
    DiscordRequestsMock.MAPLIST_MOD: [4],
    DiscordRequestsMock.EXPLIST_MOD: [5],
    DiscordRequestsMock.NEEDS_RECORDING: [6],
    DiscordRequestsMock.BANNED: [7],
    DiscordRequestsMock.MAPLIST_OWNER: [2],
    DiscordRequestsMock.EXPLIST_OWNER: [3],
}


@src.db.connection.postgres
async def set_user_roles(token: str, conn=None) -> None:
    match = re.match(r"mock_discord_(\d+)_(\d+)", token)
    if match is None:
        return

    uid = int(match.group(1))
    roles_int = int(match.group(2))
    roles = []
    for perm in perms:
        if perm & roles_int:
            roles += perms[perm]

    await conn.execute("DELETE FROM user_roles WHERE user_id = $1", uid)
    await conn.executemany(
        """
        INSERT INTO user_roles
            (user_id, role_id)
        VALUES
            ($1, $2)
        """,
        [(uid, role) for role in roles],
    )
