import src.db.connection
postgres = src.db.connection.postgres


@postgres
async def submit_run(
        map_code: str,
        black_border: bool,
        no_geraldo: bool,
        format_id: int,
        lcc_info: dict | None,  # leftover, proof
        player_id: int,
        conn=None,
) -> int:
    async with conn.transaction():
        lcc_id = None
        if lcc_info:
            lcc_id = await conn.fetchval(
                """
                INSERT INTO leastcostchimps(proof, leftover)
                VALUES($1, $2)
                RETURNING id
                """,
                lcc_info["proof"], lcc_info["leftover"]
            )
        run_id = await conn.fetchval(
            """
            INSERT INTO list_completions(map, black_border, no_geraldo, lcc, format)
            VALUES($1, $2, $3, $4, $5)
            RETURNING id
            """,
            map_code, black_border, no_geraldo, lcc_id, format_id
        )
        await conn.execute(
            """
            INSERT INTO listcomp_players(run, user_id)
            VALUES($1, $2)
            """,
            run_id, player_id
        )
        return run_id


@postgres
async def accept_run(run_id: int, conn=None) -> None:
    pass
