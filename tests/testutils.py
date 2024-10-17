import os
import config
import importlib.util


def override_config():
    spec = importlib.util.spec_from_file_location(
        name="config_test",
        location=os.path.join(os.path.abspath(os.path.dirname(__file__)), "..", "config.test.py"),
    )
    config_test = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_test)

    forced_override = [
        "PERSISTENT_DATA_PATH",
        "DB_NAME",
    ]

    for vname in vars(config_test):
        if not vname.isupper():
            continue
        if vname in forced_override:
            assert getattr(config, vname) != getattr(config_test, vname), \
                f"Must override config.{forced_override[0]} in config.test.py with a different value than config.py"
            forced_override.remove(vname)
        setattr(config, vname, getattr(config_test, vname))

    assert len(forced_override) == 0, f"Must override config.{forced_override[0]} in config.test.py"


def clear_db_patch_data():
    dbinfo_path = os.path.join(config.PERSISTENT_DATA_PATH, "data", "dbinfo.txt")
    if os.path.exists(dbinfo_path):
        os.remove(dbinfo_path)


def stringify_path(key_path: list):
    path_str = ""
    for i, key in enumerate(key_path):
        if isinstance(key, int):
            path_str += f"[{key}]"
        else:
            path_str += f".{key}"
    if path_str.startswith("."):
        path_str = path_str[1:]
    return path_str
