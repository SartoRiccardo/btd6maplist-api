import os
import io
import csv
import json
import aiofiles
import asyncio
from typing import Literal
from config import PERSISTENT_DATA_PATH
from src.utils.colors import purple
from datetime import datetime


log_path = os.path.join(PERSISTENT_DATA_PATH, "logs")
os.makedirs(log_path, exist_ok=True)


file: aiofiles.threadpool.text.AsyncTextIOWrapper | None = None


async def init_log():
    global file
    async with aiofiles.open(os.path.join(log_path, "changes.log"), "a") as logfile:
        file = logfile
        print(f"{purple('[Log]')} Logfile open")
        await asyncio.Future()


async def log_action(
        etype: Literal["map", "config", "completion"],
        action: Literal["post", "put", "delete"],
        eid: str | int | None,
        new_entity: dict | None,
) -> None:
    if file is None:
        return
    str_entity = json.dumps(new_entity)
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow([int(datetime.now().timestamp()), etype, action, str(eid), str_entity])
    await file.write(out.getvalue())
    await file.flush()

