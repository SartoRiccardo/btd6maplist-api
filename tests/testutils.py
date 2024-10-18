import os
import json
import config
import importlib.util
import aiohttp
from typing import Any


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


def to_formdata(json_data: dict) -> aiohttp.FormData:
    form_data = aiohttp.FormData()
    form_data.add_field(
        "data",
        json.dumps(json_data),
        content_type="application/json",
    )
    return form_data


def formdata_field_tester(content: list[tuple[str, Any, dict[str, Any]]]):
    for i in range(len(content)):
        form_data = aiohttp.FormData()
        for j, content_info in enumerate(content):
            if i == j:
                continue
            kwargs = {} if len(content_info) == 2 else content_info[2]
            form_data.add_field(content_info[0], content_info[1], **kwargs)
        yield form_data, content[i][0]
