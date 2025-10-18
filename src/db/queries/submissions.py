
from src.db.connection import postgres
from src.db.models.maps import PartialMap
from src.db.models.challenges import ListCompletionWithMeta, LCC
from src.db.models.MapSubmission import MapSubmission

@postgres
async def get_map_submissions_by_user(
    conn,
    user_id: int,
    page: int,
    status: str
) -> tuple[int, list[MapSubmission]]:
    offset = (page - 1) * 50
    
    status_filter = ""
    if status == "pending":
        status_filter = "AND rejected_by IS NULL"

    total_query = f"""
        SELECT COUNT(*)
        FROM map_submissions
        WHERE submitter = $1 {status_filter}
    """
    
    query = f"""
        SELECT code, submitter, subm_notes, format_id, proposed as proposed_diff, rejected_by, created_on, completion_proof, wh_data, NULL as id, NULL as wh_msg_id
        FROM map_submissions
        WHERE submitter = $1 {status_filter}
        ORDER BY created_on DESC
        LIMIT 50 OFFSET $2
    """

    total = await conn.fetchval(total_query, user_id)
    if not total:
        return 0, []

    submissions = await conn.fetch(query, user_id, offset)

    return total, [MapSubmission(**row) for row in submissions]

@postgres
async def get_completion_submissions_by_user(
    conn,
    user_id: int,
    page: int,
    status: str
) -> tuple[int, list[ListCompletionWithMeta]]:
    offset = (page - 1) * 50

    status_filter = ""
    if status == "pending":
        status_filter = "AND accepted_by IS NULL"

    total_query = f"""
        SELECT COUNT(*)
        FROM completions c
        JOIN completions_meta cm ON c.id = cm.completion
        JOIN comp_players cp ON cm.id = cp.run
        WHERE cp.user_id = $1 {status_filter}
    """

    query = f"""
        WITH user_submissions AS (
            SELECT c.id, cm.id as meta_id, c.map, c.subm_notes, c.subm_wh_payload,
                   cm.black_border, cm.no_geraldo, cm.lcc, cm.format, cm.accepted_by, cm.created_on, cm.deleted_on,
                   array_agg(cp.user_id) as user_ids
            FROM completions c
            JOIN completions_meta cm ON c.id = cm.completion
            JOIN comp_players cp ON cm.id = cp.run
            WHERE cp.user_id = $1 {status_filter}
            GROUP BY c.id, cm.id
        )
        SELECT
            us.*,
            m.name as map_name, m.r6_start, m.map_data, m.map_preview_url,
            mlm.placement_curver, mlm.placement_allver, mlm.difficulty, mlm.botb_difficulty, mlm.remake_of, mlm.optimal_heros
        FROM user_submissions us
        JOIN maps m ON us.map = m.code
        JOIN latest_maps_meta(NOW()::timestamp) mlm ON m.code = mlm.code
        ORDER BY us.created_on DESC
        LIMIT 50 OFFSET $2
    """

    total = await conn.fetchval(total_query, user_id)
    if not total:
        return 0, []

    submissions = await conn.fetch(query, user_id, offset)

    return total, [ListCompletionWithMeta(
        id=row["id"],
        map=PartialMap(
            code=row["map"], 
            name=row["map_name"], 
            placement_curver=row["placement_curver"], 
            placement_allver=row["placement_allver"], 
            difficulty=row["difficulty"], 
            botb_difficulty=row["botb_difficulty"], 
            remake_of=row["remake_of"], 
            r6_start=row["r6_start"], 
            map_data=row["map_data"], 
            deleted_on=None, # This is not available in the query
            optimal_heros=row["optimal_heros"].split(";") if row["optimal_heros"] else [],
            map_preview_url=row["map_preview_url"]
        ),
        user_ids=row["user_ids"],
        black_border=row["black_border"],
        no_geraldo=row["no_geraldo"],
        current_lcc=False, # This is not available in the query
        format=row["format"],
        lcc=LCC(id=row["lcc"], leftover=0) if row["lcc"] else None,
        subm_proof_img=[],
        subm_proof_vid=[],
        subm_notes=row["subm_notes"],
        accepted_by=row["accepted_by"],
        created_on=row["created_on"],
        deleted_on=row["deleted_on"],
        subm_wh_payload=row["subm_wh_payload"],
    ) for row in submissions]
