import src.db.connection
import re
from tests.mocks.Permissions import Permissions


@src.db.connection.postgres
async def set_user_roles(token: str, conn=None) -> None:
    """
    Discord token format: mock_discord_{uid}_{perm_list}
    - perm_list is a plus-separated array of permissions.
      Permissions can be individual or by category.
      Individual: {permission}/{format_ids, comma separated. If empty, present in all formats}
        For example: edit:config/1,51+edit:map/1+edit:self/
      Category: !{category}/{format_ids, comma separated. If empty, present in all formats}
        For example: !mod/51+!curator/1,2
        Categories are methods in the Permissions class.
      Role id: @{role_id} you can assign a role by ID, other than the test one.

      You can combine the two types: edit:config/+!mod/51+@4
    """
    match = re.match(r"mock_discord_(\d+)_(.*)", token)
    if match is None:
        return

    uid = int(match.group(1))
    perms_str = match.group(2)

    permissions: dict[int | None, set[str]] = {}
    roles = []

    for segment in perms_str.split("+"):
        if segment.startswith("!"):
            # Category permission
            category, _, id_list = segment[1:].partition("/")
            ids = [int(x) if x else None for x in id_list.split(",") if x != ""] if id_list else [None]
            perm_set = getattr(Permissions, category)()

            for format_id in ids:
                permissions.setdefault(format_id, set()).update(perm_set)
        elif segment.startswith("@"):
            # Role ID
            role_id = int(segment[1:])
            roles.append(role_id)
        elif len(segment):
            # Specific permission
            perm_type, _, rest = segment.partition(":")
            resource_type, _, id_list = rest.partition("/")
            full_perm = f"{perm_type}:{resource_type}"

            ids = [int(x) if x else None for x in id_list.split(",") if x != ""] if id_list else [None]

            for format_id in ids:
                permissions.setdefault(format_id, set()).add(full_perm)

    # Create new role in DB
    async with conn.transaction():
        await conn.execute("DELETE FROM user_roles WHERE user_id = $1", uid)

        role_id = await conn.fetchval(
            """
            INSERT INTO roles
                (name)
            VALUES
                ('test-role')
            RETURNING id
            """,
        )
        roles.append(role_id)

        role_permissions = []
        for format_id, role_perms in permissions.items():
            for perm in role_perms:
                role_permissions.append((role_id, format_id, perm))

        await conn.executemany(
            """
            INSERT INTO role_format_permissions
                (role_id, format_id, permission)
            VALUES
                ($1, $2, $3)
            """,
            role_permissions
        )

        await conn.executemany(
            """
            INSERT INTO user_roles
                (user_id, role_id)
            VALUES
                ($1, $2)
            """,
            [(uid, role_id) for role_id in roles],
        )
