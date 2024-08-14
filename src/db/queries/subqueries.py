
def get_int_config(varname):
    return f"(SELECT value FROM config WHERE name='{varname}')::int"


def sq(subquery):
    """Just shortens it. Cool for debugging"""
    return subquery.strip().replace("\n", " ").replace("\t", " ")
