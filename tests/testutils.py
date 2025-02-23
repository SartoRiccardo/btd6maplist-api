import os
import copy
import json
import config
import importlib.util
import aiohttp
from typing import Any
from collections.abc import Generator


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


def fuzz_data(
        full_data: dict,
        extra_expected: dict = None,
        int_as_float: bool = False,
) -> Generator[tuple[dict, str, list | dict | float | str | None], None, None]:
    extra_expected = {} if extra_expected is None else extra_expected
    test_values = [[], {}, 1.7, "a", "1", None]

    def create_data(key_path: list):
        request_data = copy.deepcopy(full_data)
        current_data = request_data
        extra_types = extra_expected
        for i, key in enumerate(key_path):
            if isinstance(key, str) and isinstance(extra_types, dict) and key in extra_types:
                extra_types = extra_types[key]
            if i < len(key_path) - 1:
                current_data = current_data[key]

        original_type = current_data[key_path[-1]]
        if original_type is not None:
            original_type = original_type.__class__
        if original_type is int and int_as_float:
            original_type = float

        for dtype in test_values:
            dtype_cls = dtype if dtype is None else dtype.__class__
            if isinstance(extra_types, list) and dtype_cls in extra_types or \
                    dtype_cls is original_type:
                continue
            error_path = stringify_path(key_path)
            current_data[key_path[-1]] = dtype
            yield request_data, error_path, dtype

    def fuzz_rec(current_path: list = None):
        if current_path is None:
            current_path = []
        current_data = full_data
        for key in current_path:
            current_data = current_data[key]

        if len(current_path) > 0:
            yield from create_data(current_path)
        if isinstance(current_data, dict):
            for key in current_data:
                current_path.append(key)
                yield from fuzz_rec(current_path)
                current_path.pop()
        elif isinstance(current_data, list):
            current_path.append(0)
            yield from fuzz_rec(current_path)
            current_path.pop()

    return fuzz_rec()


def invalidate_field(
        full_data: dict,
        schema: dict | list,
        validations: list[tuple[Any, str]],
        current_path: list = None
) -> Generator[tuple[dict, str, str], None, None]:
    if current_path is None:
        current_path = []

    if isinstance(schema, dict):
        for key in schema:
            if key is not None:
                current_path.append(key)
            yield from invalidate_field(full_data, schema[key], validations, current_path=current_path)
            if key is not None:
                current_path.pop()
    elif isinstance(schema, list):
        for key in schema:
            appended = 1
            request_data = copy.deepcopy(full_data)
            current_data = request_data
            for i, path_key in enumerate(current_path):
                while isinstance(current_data, list) and \
                        isinstance(current_data[0], dict | list):
                    appended += 1
                    current_path.append(0)
                    current_data = current_data[0]
                current_data = current_data[path_key]
            while isinstance(current_data, list) and \
                    isinstance(current_data[0], dict | list):
                appended += 1
                current_path.append(0)
                current_data = current_data[0]
            current_path.append(key)

            edited_path = stringify_path(current_path)
            for test_val, error_msg in validations:
                current_data[key] = test_val
                yield request_data, edited_path, error_msg

            for _ in range(appended):
                current_path.pop()


def remove_fields(data_current: Any, full_data: dict = None, current_path=None) -> Generator[tuple[dict, str], None, None]:
    if current_path is None:
        current_path = []
    if full_data is None:
        full_data = data_current

    if isinstance(data_current, dict):
        for key in data_current:
            current_path.append(key)
            yield from remove_fields(data_current[key], full_data=full_data, current_path=current_path)
            current_path.pop()

            request_data = copy.deepcopy(full_data)
            data_part = request_data
            for path_key in current_path:
                data_part = data_part[path_key]
            del data_part[key]
            yield request_data, stringify_path(current_path + [key])
    elif isinstance(data_current, list) and len(data_current):
        current_path.append(0)
        yield from remove_fields(data_current[0], full_data=full_data, current_path=current_path)
        current_path.pop()
