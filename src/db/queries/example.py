import bot.db.connection
postgres = bot.db.connection.postgres


@postgres
async def get_youngsters(year: int, conn=None):
    payload = await conn.fetch("SELECT id, name FROM users WHERE born_year>$1", year)
    return [{"id": row[0], "name": row[1]} for row in payload]
