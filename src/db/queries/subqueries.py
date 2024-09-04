
def get_int_config(varname):
    return f"(SELECT value FROM config WHERE name='{varname}')::int"
